# web stuff
from flask import Flask, url_for, request, json, render_template
import gravitty


app = Flask(__name__)


@app.route('/')
def show():
    return render_template('index.html', myjson = graph_json)


@app.route('/<screen_name>')
def get_screen_name(screen_name):
    if screen_name in gravitty.available():
        graph_json = gravitty.load(screen_name)
        return render_template('index.html', myjson = graph_json )


if __name__ == '__main__':
    graph_json = gravitty.load('ZipfianAcademy')
    app.run(debug=True)
