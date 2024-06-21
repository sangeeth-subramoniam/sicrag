from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/robots933456.txt')
def health_check():
    return 'Healthy', 200

if __name__ == '__main__':
    app.run(debug=True)
