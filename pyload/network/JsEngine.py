# -*- coding: utf-8 -*-
# @author: vuolter

import subprocess
import sys

from os import path
from urllib import quote

from pyload.utils import encode, decode, uniqify


class JsEngine(object):
    """ JS Engine superclass """

    def __init__(self, core, engine=None):
        self.core   = core
        self.engine = None  #: Engine Instance

        if not engine:
            engine = self.core.config.get("general", "jsengine")

        if engine != "auto" and self.set(engine) is False:
            engine = "auto"
            self.core.log.warning("JS Engine set to \"auto\" for safely")

        if engine == "auto":
            for E in self.find():
                if self.set(E) is True:
                    break
            else:
                self.core.log.error("No JS Engine available")


    @classmethod
    def find(cls):
        """ Check if there is any engine available """
        return [E for E in ENGINES if E.find()]


    def get(self, engine=None):
        """ Convert engine name (string) to relative JSE class (AbstractEngine extended) """
        if not engine:
            JSE = self.engine

        elif isinstance(engine, basestring):
            engine_name = engine.lower()
            for E in ENGINES:
                if E.__name == engine_name:  #: doesn't check if E(NGINE) is available, just convert string to class
                    JSE = E
                    break
            else:
                raise ValueError("JSE")

        elif issubclass(engine, AbstractEngine):
            JSE = engine

        else:
            raise TypeError("engine")

        return JSE


    def set(self, engine):
        """ Set engine name (string) or JSE class (AbstractEngine extended) as default engine """
        if isinstance(engine, basestring):
            return self.set(self.get(engine))

        elif issubclass(engine, AbstractEngine) and engine.find():
            self.engine = engine
            return True

        else:
            return False


    def eval(self, script, engine=None):  #: engine can be a jse name """string""" or an AbstractEngine """class"""
        JSE = self.get(engine)

        if not JSE:
            raise TypeError("engine")

        script = encode(script)

        out, err = JSE.eval(script)

        results = [out]

        if self.core.config.get("general", "debug"):
            if err:
                self.core.log.debug(JSE.__name + ":", err)

            engines = self.find()
            engines.remove(JSE)
            for E in engines:
                out, err = E.eval(script)
                res = err or out
                self.core.log.debug(E.__name + ":", res)
                results.append(res)

            if len(results) > 1 and len(uniqify(results)) > 1:
                self.core.log.warning("JS output of two or more engines mismatch")

        return results[0]


class AbstractEngine(object):
    """ JSE base class """

    __name = ""


    def __init__(self):
        self.setup()
        self.available = self.find()


    def setup(self):
        pass


    @classmethod
    def find(cls):
        """ Check if the engine is available """
        try:
            __import__(cls.__name)
        except Exception:
            try:
                out, err = cls().eval("print(23+19)")
            except Exception:
                res = False
            else:
                res = out == "42"
        else:
            res = True

        return res


    def _eval(args):
        if not self.available:
            return None, "JS Engine \"%s\" not found" % self.__name

        try:
            p = subprocess.Popen(args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 bufsize=-1)
            return map(lambda x: x.strip(), p.communicate())
        except Exception, e:
            return None, e


    def eval(script):
        raise NotImplementedError


class Pyv8Engine(AbstractEngine):

    __name = "pyv8"


    def eval(self, script):
        if not self.available:
            return None, "JS Engine \"%s\" not found" % self.__name

        try:
            rt = PyV8.JSContext()
            rt.enter()
            res = rt.eval(script), None  #@TODO: parse stderr
        except Exception, e:
            res = None, e

        return res


class CommonEngine(AbstractEngine):

    __name = "js"


    def setup(self):
        subprocess.Popen(["js", "-v"], bufsize=-1).communicate()


    def eval(self, script):
        script = "print(eval(unescape('%s')))" % quote(script)
        args = ["js", "-e", script]
        return self._eval(args)


class NodeEngine(AbstractEngine):

    __name = "nodejs"


    def setup(self):
        subprocess.Popen(["node", "-v"], bufsize=-1).communicate()


    def eval(self, script):
        script = "console.log(eval(unescape('%s')))" % quote(script)
        args = ["node", "-e", script]
        return self._eval(args)


class RhinoEngine(AbstractEngine):

    __name = "rhino"


    def setup(self):
        jspath = [
            "/usr/share/java*/js.jar",
            "js.jar",
            path.join(pypath, "js.jar")
        ]
        for p in jspath:
            if path.exists(p):
                self.path = p
                break
        else:
            self.path = ""


    def eval(self, script):
        script = "print(eval(unescape('%s')))" % quote(script)
        args = ["java", "-cp", self.path, "org.mozilla.javascript.tools.shell.Main", "-e", script]
        res = decode(self._eval(args))
        try:
            return res.encode("ISO-8859-1")
        finally:
            return res


class JscEngine(AbstractEngine):

    __name = "javascriptcore"


    def setup(self):
        jspath = "/System/Library/Frameworks/JavaScriptCore.framework/Resources/jsc"
        self.path = jspath if path.exists(jspath) else ""


    def eval(self, script):
        script = "print(eval(unescape('%s')))" % quote(script)
        args = [self.path, "-e", script]
        return self._eval(args)


#@NOTE: Priority ordered
ENGINES = [CommonEngine, Pyv8Engine, NodeEngine, RhinoEngine]

if sys.platform == "darwin":
    ENGINES.insert(JscEngine)