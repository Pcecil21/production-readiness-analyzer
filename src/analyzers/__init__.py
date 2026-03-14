from .security import SecurityAnalyzer
from .infrastructure import InfrastructureAnalyzer
from .code_quality import CodeQualityAnalyzer
from .testing import TestingAnalyzer
from .platform_compat import PlatformCompatAnalyzer

ALL_ANALYZERS = [
    SecurityAnalyzer,
    InfrastructureAnalyzer,
    CodeQualityAnalyzer,
    TestingAnalyzer,
    PlatformCompatAnalyzer,
]
