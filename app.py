from flask import Flask, render_template, request, make_response
from airium import Airium
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        req1 = request.form.get('input_req')
        protocol = request.form.get('protocol')
        alert = 0

        try:
            method = req1.split(' ')[0]
            path = req1.split(' ')[1]
            host = req1.split('\n')[1]
            body = req1.split(os.linesep + os.linesep)[-1]

            if protocol == 'https':
                url = 'https://' + host.split(' ')[1] + path
            else:
                url = 'http://' + host.split(' ')[1] + path

            body = body.split('\n\n')[-1]
            body = body.split('&')
        except:
            return render_template('index.html', alert=1)

        a=Airium()
        with a.html():
            with a.body():
                with a.form(action=url, method=method):
                    for i in body:
                        if "\n" in i:
                            i = i.replace("\n", "")
                        a.input(type='hidden', name=i.split('=')[0], value=i.split('=')[1])
                with a.script():
                    a('document.forms[0].submit()')
        poc = str(a)

        response = make_response(render_template('index.html', poc=poc))

        return response

    else:
        return render_template('index.html')

if __name__ == '__main__':
    #app.run()
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)
