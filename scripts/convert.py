#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash Rule Provider 转换为 Surge RULE-SET 脚本

将 clash/custom-proxy.txt 与 clash/custom-direct.txt 中的规则
转换为 Surge 兼容的 RULE-SET 规则集 (surge/*.list)

语法转换规则：
- '+.domain.com' -> 'DOMAIN-SUFFIX,domain.com'
- 'domain.com'   -> 'DOMAIN,domain.com' (若已存在通配规则，则自动去重)
"""

import sys
from pathlib import Path


def parse_clash_rules(file_path: Path):
    """
    解析 Clash domain provider 文件中的规则条目。
    支持：
      - '+.example.com'
      - 'example.com'
      - 单双引号及无引号形式
      - 过滤行内注释与 YAML payload 标记
    """
    suffixes = set()
    exacts = set()

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("payload:"):
                continue

            # 移除行首的 YAML 列表项标记
            if line.startswith("-"):
                line = line[1:].strip()

            # 移除行内注释
            line = line.split("#")[0].strip()

            # 移除包裹的单双引号
            line = line.strip("'\"").strip()

            if not line:
                continue

            # 过滤明显无效的非域名字符（如冒号、斜杠、空格等）
            if any(c in line for c in (":", "/", "\\", " ")):
                continue

            # 处理通配域名 (+.domain 或 .domain)
            if line.startswith("+."):
                domain = line[2:].strip().lower()
                if domain:
                    suffixes.add(domain)
            elif line.startswith("."):
                domain = line[1:].strip().lower()
                if domain:
                    suffixes.add(domain)
            else:
                domain = line.lower()
                if domain:
                    exacts.add(domain)

    # 智能去重：DOMAIN-SUFFIX,domain 已经天然匹配根域及所有子域名，无需重复添加 DOMAIN,domain
    exacts = {d for d in exacts if d not in suffixes}

    return sorted(suffixes), sorted(exacts)


def generate_surge_rule_set(src_path: Path, dst_path: Path):
    """将提取的规则写入 Surge RULE-SET 格式文件"""
    if not src_path.exists():
        print(f"[-] 警告: 源文件不存在: {src_path}", file=sys.stderr)
        return

    suffixes, exacts = parse_clash_rules(src_path)

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Generated automatically from {src_path.name} for Surge RULE-SET",
        "# Do not edit manually.",
        "",
    ]

    for s in suffixes:
        lines.append(f"DOMAIN-SUFFIX,{s}")

    for e in exacts:
        lines.append(f"DOMAIN,{e}")

    lines.append("")  # 末尾空行

    dst_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] 成功转换: {src_path} -> {dst_path} (DOMAIN-SUFFIX: {len(suffixes)}, DOMAIN: {len(exacts)})")


def main():
    repo_root = Path(__file__).resolve().parent.parent

    tasks = [
        (repo_root / "clash" / "custom-proxy.txt", repo_root / "surge" / "custom-proxy.list"),
        (repo_root / "clash" / "custom-direct.txt", repo_root / "surge" / "custom-direct.list"),
    ]

    for src, dst in tasks:
        generate_surge_rule_set(src, dst)


if __name__ == "__main__":
    main()
