import os
from app import app

port = int(os.getenv('PORT', 5001))
host = os.getenv('HOST', '0.0.0.0')

print(f"正在启动服务器... :{port}")
print("API Key 已配置:", bool(app.config.get('DEEPSEEK_API_KEY', '')))
key = app.config.get('DEEPSEEK_API_KEY', '')
print("Key 结尾:", key[-8:] if key else "无")
app.run(debug=False, host=host, port=port)
