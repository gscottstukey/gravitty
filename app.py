# web stuff
from flask import Flask, url_for, request, json, render_template
import sys
import gravitty


app = Flask(__name__)


@app.route('/')
def show_default():
    graph_json = gravitty.load('graphlabteam')
    available = gravitty.available()
    available.sort()

    return render_template('index.html',
                           myjson = graph_json,
                           available_screennames = available )

@app.route('/<screen_name>')
def get_screen_name(screen_name):

    available = gravitty.available()
    available.sort()

    if screen_name in available or screen_name == '':
        graph_json = gravitty.load(screen_name)
        return render_template('index.html',
                               myjson = graph_json,
                               available_screennames = available )

    else:
        return render_template('does_not_exist.html',
                               screen_name=screen_name,
                               available_screennames = available )

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            port = int(argv[1])
        except:
            print 'Port must be an integer'
            sys.exit(1)
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        app.run(debug=True)
