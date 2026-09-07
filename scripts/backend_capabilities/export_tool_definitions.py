"""Regenerate the checked-in Tool Gateway schema catalogue deterministically."""
import json
from pathlib import Path
from backend.app.tools.registry import export_tool_definitions

ROOT=Path(__file__).resolve().parents[2]

def main():
    target=ROOT/'backend/app/tools/definitions.json'
    target.write_text(json.dumps(export_tool_definitions(),indent=2)+'\n',encoding='utf-8')
    print({'definitions':str(target),'total_tools':export_tool_definitions()['total_tools']})

if __name__=='__main__': main()
