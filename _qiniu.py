# -*- coding: utf-8 -*-
import config
import sys

import qiniu.rs
import qiniu.io

class PutPolicy(object):
    scope = 'pixiv'
    expires = 3600
    callbackUrl = None
    callbackBody = None
    returnUrl = None
    returnBody = None
    endUser = None
    asyncOps = None

    def __init__(self, scope):
        self.scope = scope

def upload(f):
    # 获取上传凭证
    policy = qiniu.rs.PutPolicy(qiniu.conf.BUCKET_NAME)
    uptoken = policy.token()

    # 上传
    ret, err = qiniu.io.put_file(uptoken, f, f)

    return True