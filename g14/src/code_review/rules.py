"""代码审查规则集配置"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Severity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RuleCategory(str, Enum):
    """规则类别"""
    BUG = "bug"
    CODE_SMELL = "code_smell"
    SECURITY = "security"
    STYLE = "style"
    PERFORMANCE = "performance"


@dataclass
class Rule:
    """单个审查规则"""
    id: str
    name: str
    description: str
    category: RuleCategory
    severity: Severity
    language: str
    enabled: bool = True


@dataclass
class RuleSet:
    """规则集"""
    name: str
    description: str
    rules: Dict[str, Rule] = field(default_factory=dict)

    def get_enabled_rules(self, language: Optional[str] = None) -> List[Rule]:
        """获取启用的规则"""
        return [
            rule for rule in self.rules.values()
            if rule.enabled and (language is None or rule.language == language)
        ]


PEP8_RULES: Dict[str, Rule] = {
    "E101": Rule(
        id="E101",
        name="mixed-indentation",
        description="缩进包含制表符和空格的混合使用",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E111": Rule(
        id="E111",
        name="indentation-not-multiple-of-four",
        description="缩进不是 4 的倍数",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E201": Rule(
        id="E201",
        name="whitespace-after-bracket",
        description="括号后有多余空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E202": Rule(
        id="E202",
        name="whitespace-before-bracket",
        description="括号前有多余空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E225": Rule(
        id="E225",
        name="missing-whitespace-around-operator",
        description="运算符周围缺少空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E231": Rule(
        id="E231",
        name="missing-whitespace-after-comma",
        description="逗号后缺少空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E301": Rule(
        id="E301",
        name="expected-2-blank-lines",
        description="函数或类定义之间需要 2 个空行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E302": Rule(
        id="E302",
        name="expected-2-blank-lines-found-1",
        description="函数或类定义之间需要 2 个空行，只找到 1 个",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E401": Rule(
        id="E401",
        name="multiple-imports-on-one-line",
        description="一行导入多个模块",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E402": Rule(
        id="E402",
        name="module-level-import-not-at-top",
        description="模块级导入不在文件顶部",
        category=RuleCategory.STYLE,
        severity=Severity.MEDIUM,
        language="python"
    ),
    "E501": Rule(
        id="E501",
        name="line-too-long",
        description="行长度超过 88 个字符",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E701": Rule(
        id="E701",
        name="multiple-statements-on-one-line",
        description="一行包含多条语句",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "E711": Rule(
        id="E711",
        name="comparison-to-None-should-be-is",
        description="与 None 比较应使用 'is' 而不是 '=='",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="python"
    ),
    "E712": Rule(
        id="E712",
        name="comparison-to-True-should-be-if-cond",
        description="与 True/False 比较应直接使用条件判断",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="python"
    ),
    "E722": Rule(
        id="E722",
        name="bare-except",
        description="使用裸 except 而不指定异常类型",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="python"
    ),
    "F401": Rule(
        id="F401",
        name="unused-import",
        description="导入但未使用的模块",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="python"
    ),
    "F403": Rule(
        id="F403",
        name="star-imports",
        description="使用通配符导入 'from module import *'",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.MEDIUM,
        language="python"
    ),
    "F811": Rule(
        id="F811",
        name="redefinition-of-unused-variable",
        description="重新定义了未使用的变量",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="python"
    ),
    "F821": Rule(
        id="F821",
        name="undefined-name",
        description="使用了未定义的名称",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="python"
    ),
    "F841": Rule(
        id="F841",
        name="unused-variable",
        description="赋值但未使用的变量",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="python"
    ),
    "W191": Rule(
        id="W191",
        name="tab-indenteration",
        description="使用制表符缩进",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W291": Rule(
        id="W291",
        name="trailing-whitespace",
        description="行尾有多余空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W292": Rule(
        id="W292",
        name="no-newline-at-end-of-file",
        description="文件末尾缺少空行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W293": Rule(
        id="W293",
        name="blank-line-contains-whitespace",
        description="空行包含空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W391": Rule(
        id="W391",
        name="blank-line-at-end-of-file",
        description="文件末尾有多余空行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W503": Rule(
        id="W503",
        name="line-break-after-operator",
        description="运算符后换行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W504": Rule(
        id="W504",
        name="line-break-after-operator",
        description="运算符后换行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="python"
    ),
    "W601": Rule(
        id="W601",
        name="has-key-is-deprecated",
        description="使用了已弃用的 .has_key() 方法",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="python"
    ),
    "W603": Rule(
        id="W603",
        name="backtick-is-deprecated",
        description="使用了已弃用的反引号",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="python"
    ),
}


ESLINT_RULES: Dict[str, Rule] = {
    "no-undef": Rule(
        id="no-undef",
        name="no-undefined-variables",
        description="禁止使用未声明的变量",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "no-unused-vars": Rule(
        id="no-unused-vars",
        name="no-unused-variables",
        description="禁止未使用的变量",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-console": Rule(
        id="no-console",
        name="no-console",
        description="禁止使用 console",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-alert": Rule(
        id="no-alert",
        name="no-alert",
        description="禁止使用 alert、confirm、prompt",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-debugger": Rule(
        id="no-debugger",
        name="no-debugger",
        description="禁止使用 debugger",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "no-eval": Rule(
        id="no-eval",
        name="no-eval",
        description="禁止使用 eval()",
        category=RuleCategory.SECURITY,
        severity=Severity.CRITICAL,
        language="javascript"
    ),
    "no-implied-eval": Rule(
        id="no-implied-eval",
        name="no-implied-eval",
        description="禁止使用隐式 eval()",
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "no-new-func": Rule(
        id="no-new-func",
        name="no-new-func",
        description="禁止使用 Function 构造函数",
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "no-script-url": Rule(
        id="no-script-url",
        name="no-script-url",
        description="禁止使用 javascript: 链接",
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "xss/no-mixed-html": Rule(
        id="xss/no-mixed-html",
        name="no-mixed-html",
        description="防止 XSS 攻击",
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "eqeqeq": Rule(
        id="eqeqeq",
        name="eqeqeq",
        description="要求使用 === 和 !==",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "no-eq-null": Rule(
        id="no-eq-null",
        name="no-eq-null",
        description="禁止与 null 进行宽松比较",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "no-extra-boolean-cast": Rule(
        id="no-extra-boolean-cast",
        name="no-extra-boolean-cast",
        description="禁止不必要的布尔类型转换",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-extra-semi": Rule(
        id="no-extra-semi",
        name="no-extra-semicolons",
        description="禁止不必要的分号",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "semi": Rule(
        id="semi",
        name="semicolon",
        description="要求或禁止使用分号",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "quotes": Rule(
        id="quotes",
        name="quotes",
        description="强制使用一致的引号风格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "indent": Rule(
        id="indent",
        name="indentation",
        description="强制使用一致的缩进",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "max-len": Rule(
        id="max-len",
        name="max-line-length",
        description="强制行的最大长度",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-trailing-spaces": Rule(
        id="no-trailing-spaces",
        name="no-trailing-spaces",
        description="禁止行尾空格",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-multiple-empty-lines": Rule(
        id="no-multiple-empty-lines",
        name="no-multiple-empty-lines",
        description="禁止多行空行",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "camelcase": Rule(
        id="camelcase",
        name="camelcase",
        description="强制使用驼峰命名法",
        category=RuleCategory.STYLE,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-var": Rule(
        id="no-var",
        name="no-var",
        description="要求使用 let 或 const 而不是 var",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "prefer-const": Rule(
        id="prefer-const",
        name="prefer-const",
        description="要求使用 const 声明不修改的变量",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-use-before-define": Rule(
        id="no-use-before-define",
        name="no-use-before-define",
        description="禁止在变量定义之前使用",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "no-redeclare": Rule(
        id="no-redeclare",
        name="no-redeclare",
        description="禁止重新声明变量",
        category=RuleCategory.BUG,
        severity=Severity.MEDIUM,
        language="javascript"
    ),
    "no-dupe-keys": Rule(
        id="no-dupe-keys",
        name="no-duplicate-keys",
        description="禁止对象字面量中出现重复的键",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "no-dupe-args": Rule(
        id="no-dupe-args",
        name="no-duplicate-arguments",
        description="禁止 function 定义中出现重复参数",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="javascript"
    ),
    "no-empty": Rule(
        id="no-empty",
        name="no-empty-blocks",
        description="禁止空块语句",
        category=RuleCategory.CODE_SMELL,
        severity=Severity.LOW,
        language="javascript"
    ),
    "no-constant-condition": Rule(
        id="no-constant-condition",
        name="no-constant-condition",
        description="禁止在条件中使用常量表达式",
        category=RuleCategory.BUG,
        severity=Severity.HIGH,
        language="javascript"
    ),
}


LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
}


def get_pep8_ruleset() -> RuleSet:
    """获取 PEP8 规则集"""
    return RuleSet(
        name="PEP8",
        description="Python 代码风格规范",
        rules=PEP8_RULES.copy()
    )


def get_eslint_ruleset() -> RuleSet:
    """获取 ESLint 规则集"""
    return RuleSet(
        name="ESLint",
        description="JavaScript/TypeScript 代码规范",
        rules=ESLINT_RULES.copy()
    )


def get_all_rulesets() -> Dict[str, RuleSet]:
    """获取所有规则集"""
    return {
        "pep8": get_pep8_ruleset(),
        "eslint": get_eslint_ruleset(),
    }


def get_rules_for_language(language: str) -> List[Rule]:
    """获取指定语言的所有规则"""
    all_rules = []
    for ruleset in get_all_rulesets().values():
        all_rules.extend(ruleset.get_enabled_rules(language))
    return all_rules
