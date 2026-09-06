#!/usr/bin/env python3
"""
将记录字段 JSON 写入 UTF-8（无 BOM）文件，供 lark-cli --json @file 使用。

解决 PowerShell 环境下的两个痛点：
1. 中文 JSON 直接作为命令行参数时引号被剥离、编码错乱
2. lark-cli 只允许从工作目录/临时目录/files 目录读取 @file

用法（推荐用管道 + --stdin，避免 PowerShell 引号剥离）：
    echo '{"平台名称":"模课"}' | python write_record_json.py --stdin
    python write_record_json.py '{"平台名称":"模课"}'   # 仅在非 PowerShell 环境下可靠

输出：写入当前工作目录下的 _record_payload.json，并打印文件名。
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Write record JSON to UTF-8 file for lark-cli")
    parser.add_argument("fields_json", nargs="?", help="单条记录的字段 JSON 字符串")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取 JSON")
    parser.add_argument("--output", default="_record_payload.json", help="输出文件名（默认 _record_payload.json）")
    parser.add_argument("--batch", action="store_true", help="输入已是完整 create_records 结构，不再包裹")
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    elif args.fields_json:
        raw = args.fields_json
    else:
        print("错误：请提供 fields_json 参数或使用 --stdin", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"错误：JSON 解析失败 - {e}", file=sys.stderr)
        sys.exit(1)

    if not args.batch:
        # 包裹为 batch_create 需要的结构
        payload = {"create_records": [data]}
    else:
        payload = data

    out_path = Path.cwd() / args.output
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(out_path.name)


if __name__ == "__main__":
    main()
