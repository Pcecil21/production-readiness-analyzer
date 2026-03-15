"""Operations checks: containers, orchestration, IaC, backups."""

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class OperationsChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        # OPS-001: Container configuration
        has_dockerfile = self._has_file("Dockerfile", "Containerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
        if not has_dockerfile:
            findings.append(Finding(
                check_id="OPS-001",
                category="operations",
                severity=Severity.WARNING,
                message="No Dockerfile or docker-compose config found — deployment may not be reproducible",
            ))
            score -= 15

        # OPS-002: Orchestration manifests
        k8s_files = [
            f for f in self.files
            if f.suffix in (".yml", ".yaml")
            and any(kw in self._read_safe(f, max_bytes=500) for kw in ["apiVersion:", "kind: Deployment", "kind: Service"])
        ]
        helm_files = [f for f in self.files if f.name == "Chart.yaml" or "templates" in str(f)]
        if not k8s_files and not helm_files:
            findings.append(Finding(
                check_id="OPS-002",
                category="operations",
                severity=Severity.INFO,
                message="No Kubernetes manifests or Helm charts found",
            ))
            score -= 5

        # OPS-003: Infrastructure as Code
        iac_indicators = [".tf", ".hcl", "pulumi", "cdk", "cloudformation", "serverless.yml"]
        has_iac = any(
            any(ind in f.name.lower() or f.suffix == ind for ind in iac_indicators)
            for f in self.files
        )
        if not has_iac:
            findings.append(Finding(
                check_id="OPS-003",
                category="operations",
                severity=Severity.INFO,
                message="No Infrastructure as Code (Terraform, Pulumi, CDK, etc.) detected",
            ))
            score -= 5

        # OPS-004: .dockerignore
        if has_dockerfile:
            has_dockerignore = self._has_file(".dockerignore")
            if not has_dockerignore:
                findings.append(Finding(
                    check_id="OPS-004",
                    category="operations",
                    severity=Severity.WARNING,
                    message="Dockerfile present but no .dockerignore — images may contain unnecessary files",
                ))
                score -= 10

        # OPS-005: Environment-specific configs
        env_config_patterns = [
            "config.prod", "config.staging", "config.production",
            "settings.prod", "env.production",
        ]
        has_env_configs = any(
            any(p in f.name.lower() for p in env_config_patterns)
            for f in self.files
        )
        if not has_env_configs:
            findings.append(Finding(
                check_id="OPS-005",
                category="operations",
                severity=Severity.INFO,
                message="No environment-specific configuration files detected",
            ))
            score -= 5

        return CategoryResult(name="operations", score=max(0, score), findings=findings)
