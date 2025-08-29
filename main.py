import logging
from flask import Flask, jsonify
from tasks.dispatcher_worker import bp_tasks
from tasks.dispatcher_worker import bp_tasks
from Module01.module01_flask import module01
from Module02.module02_flask import module02
from Module03.module03_flask import module03
from Module04.module04_flask import module04
from Module05.module05_flask import module05
from Module06.module06_flask import module06
from Module07.module07_flask import module07
from Module08.module08_flask import module08
from Module09.module09_flask import module09
from Module10.module10_flask import module10
from Module11.module11_flask import module11
from Module12.module12_flask import module12
from Module13.module13_flask import module13

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.register_blueprint(bp_tasks, url_prefix='/tasks')
app.register_blueprint(module01, url_prefix='/module01')
app.register_blueprint(module02, url_prefix='/module02')
app.register_blueprint(module03, url_prefix='/module03')
app.register_blueprint(module04, url_prefix='/module04')
app.register_blueprint(module05, url_prefix='/module05')
app.register_blueprint(module06, url_prefix='/module06')
app.register_blueprint(module07, url_prefix='/module07')
app.register_blueprint(module08, url_prefix='/module08')
app.register_blueprint(module09, url_prefix='/module09')
app.register_blueprint(module10, url_prefix='/module10')
app.register_blueprint(module11, url_prefix='/module11')
app.register_blueprint(module12, url_prefix='/module12')
app.register_blueprint(module13, url_prefix='/module13')


# 跨域支持
def after_request(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


app.after_request(after_request)


@app.errorhandler(500)
def bad_request(error):
    response = {'code': 500, 'msg': str(error.original_exception), 'data': {}}
    # return jsonify({"msg": "Bad Request", "status": 400}), 400
    return jsonify(response)


# @app.before_request
# def process_request():
#     # request session redirect render_template
#     # print("所有请求之前都会执行这个函数")
#     pass


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logging.basicConfig(format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
