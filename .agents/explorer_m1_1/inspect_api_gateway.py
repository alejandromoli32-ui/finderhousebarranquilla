with open(".agents/explorer_survey_1/metrocuadrado_script_28.txt", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

pos = text.find("execute-api")
if pos != -1:
    print(text[max(0, pos-200):pos+400])
