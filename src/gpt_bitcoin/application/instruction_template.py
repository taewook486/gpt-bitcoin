"""
Instruction template engine for variable substitution.

This module provides a Jinja2-like template engine for instruction files,
with support for:
- Variable substitution: {{COIN_NAME}}, {{TICKER}}, {{STRATEGY_NAME}}, etc.
- Conditional section rendering with {% if ... %} syntax
- File modification time tracking for cache invalidation
- Error handling for missing variables and files
"""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog

from gpt_bitcoin.domain.models.cryptocurrency import (
    Cryptocurrency,
    TradingStrategy,
)

logger = structlog.get_logger(__name__)


@dataclass
class TemplateVariables:
    """
    Variables available for template substitution.

    Attributes:
        coin: Cryptocurrency enum value
        ticker: Upbit ticker symbol
        strategy: TradingStrategy enum value
        strategy_file: Strategy instruction file name
        coin_description: Optional coin-specific description
        coin_specific_considerations: Optional coin-specific considerations
    """

    coin: Cryptocurrency
    ticker: str
    strategy: TradingStrategy
    strategy_file: str
    coin_description: str | None = None
    coin_specific_considerations: str | None = None


class InstructionTemplateEngine:
    """
    Jinja2-like template engine for instruction files.

    @MX:NOTE Template syntax follows Jinja2 conventions with {{ }} for variables
    and {% %} for control structures.

    Attributes:
        instructions_dir: Root directory for instruction files
    """

    # Regex patterns for template syntax
    VARIABLE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    CONDITIONAL_PATTERN = re.compile(r"\{\%\s*if\s+(.+?)\s*\%\}")

    def __init__(self, instructions_dir: Path):
        """
        Initialize template engine.

        Args:
            instructions_dir: Root directory for instruction files
        """
        self.instructions_dir = Path(instructions_dir)
        logger.info(
            "Instruction template engine initialized",
            instructions_dir=str(self.instructions_dir),
        )

    def render(self, template: str, variables: TemplateVariables) -> str:
        """
        Render template with variable substitution.

        Args:
            template: Template content with {{VAR}} placeholders
            variables: Variable values for substitution

        Returns:
            Rendered template with variables substituted

        Raises:
            DataFetchError: If template file cannot be read
        """
        # Perform variable substitution
        result = self._substitute_variables(template, variables)

        # Process conditional sections
        result = self._process_conditionals(result, variables)

        # Remove extra whitespace
        result = result.strip()

        return result

    def _substitute_variables(self, template: str, variables: TemplateVariables) -> str:
        """Substitute {{VAR}} placeholders with actual values."""
        # Build replacement dictionary
        replacements = {
            "COIN_NAME": variables.coin.display_name,
            "TICKER": variables.ticker,
            "STRATEGY_NAME": variables.strategy.display_name,
            "STRATEGY_FILE": variables.strategy_file,
        }

        # Add optional variables
        if variables.coin_description:
            replacements["COIN_DESCRIPTION"] = variables.coin_description
        if variables.coin_specific_considerations:
            replacements["COIN_SPECIFIC_CONSIDERATIONS"] = variables.coin_specific_considerations

        # Perform substitution
        result = template
        for key, value in replacements.items():
            result = result.replace(f"{{{{{key}}}}}", value)

        return result

    def _process_conditionals(self, content: str, variables: TemplateVariables) -> str:
        """
        Process conditional sections with {% if condition %} ... {% endif %} syntax.

        Args:
            content: Template content with conditional sections
            variables: Variable values for substitution

        Returns:
            Processed content with conditionals resolved
        """
        # Find all conditional blocks
        lines = content.split("\n")
        result_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for conditional start
            match = self.CONDITIONAL_PATTERN.match(line.strip())
            if match:
                condition = match.group(1).strip()
                # Find matching {% endif %}
                nested = 1
                block_lines = []
                i += 1
                while i < len(lines) and nested > 0:
                    if self.CONDITIONAL_PATTERN.match(lines[i].strip()):
                        nested += 1
                    elif "{% endif %}" in lines[i]:
                        nested -= 1
                        if nested == 0:
                            break
                    block_lines.append(lines[i])
                    i += 1

                # Evaluate condition
                if self._evaluate_condition(condition, variables):
                    result_lines.extend(block_lines)
            else:
                result_lines.append(line)
                i += 1

        return "\n".join(result_lines)

    def _evaluate_condition(self, condition: str, variables: TemplateVariables) -> bool:
        """
        Evaluate conditional expression.

        Args:
            condition: Condition string (e.g., "coin == 'BTC'")
            variables: Variable values for substitution

        Returns:
            Boolean result of condition evaluation
        """
        # Simple condition evaluation
        # Support: variable_name == 'value', variable_name != 'value'
        eq_match = re.match(r"(\w+)\s*==\s*['\"](.+?)['\"]", condition)
        if eq_match:
            var_name = eq_match.group(1)
            expected = eq_match.group(2)

            # Get variable value
            var_value = getattr(variables, var_name.lower(), None)
            if var_value is None:
                return False

            # Compare
            if isinstance(var_value, enum.Enum):
                return var_value.value == expected
            return str(var_value) == expected

        neq_match = re.match(r"(\w+)\s*!=\s*['\"](.+?)['\"]", condition)
        if neq_match:
            var_name = neq_match.group(1)
            expected = neq_match.group(2)

            # Get variable value
            var_value = getattr(variables, var_name.lower(), None)
            if var_value is None:
                return True

            # Compare
            if isinstance(var_value, enum.Enum):
                return var_value.value != expected
            return str(var_value) != expected

        # Default: unknown condition, include content
        logger.warning(
            "Unknown condition format, including content",
            condition=condition,
        )
        return True

    def get_file_modification_time(self, file_path: Path) -> float | None:
        """
        Get file modification time for cache invalidation.

        Args:
            file_path: Path to instruction file

        Returns:
            Modification time as float, or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        return file_path.stat().st_mtime

    def validate_template(self, template: str) -> list[str]:
        """
        Validate template for syntax errors.

        Args:
            template: Template content to validate

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        # Check for unclosed variable tags
        unclosed_vars = re.findall(r"\{\{[^}]*$", template)
        if unclosed_vars:
            errors.append(f"Unclosed variable tags: {unclosed_vars}")

        # Check for unclosed conditional tags
        if_count = len(re.findall(r"\{\%\s*if\s+", template))
        endif_count = len(re.findall(r"\{\%\s*endif\s*\%\}", template))
        if if_count != endif_count:
            errors.append(f"Mismatched conditional tags: {if_count} if, {endif_count} endif")

        return errors


import enum  # Add this import for condition evaluation
