import json
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from local_app.conversation import Conversation, validate_plan
from local_app.core import Store, messages_for
from local_app.server import Application, Handler, ThreadingHTTPServer


class PlanTests(unittest.TestCase):
    def test_unsupported_action_and_scene_cannot_escape_allowlist(self):
        plan = validate_plan({"reply":"Hello", "presentation":"execute", "scene":"../../secret", "action":"run_code", "facts":[]}, "hi", "auto", "mira", ["mira"])
        self.assertEqual((plan["presentation"], plan["scene"]), ("text", "mira"))
        self.assertEqual(plan["action"], "none")

    def test_call_continues_and_unavailable_picture_is_not_promised(self):
        data = {"reply":"Hello", "presentation":"continue", "scene":"keep", "facts":[]}
        self.assertEqual(validate_plan(data,"hi","video","cafe",["cafe"])["presentation"],"video")
        data["presentation"] = "portrait"
        self.assertEqual(validate_plan(data,"show me","auto","mira",[])["presentation"],"text")

    def test_only_verbatim_bounded_facts_from_latest_user_turn_survive(self):
        data = {"reply":"Hi Alex", "facts":[{"key":"user_name","quote":"My name is Alex"},{"key":"job","quote":"I am a doctor"}]}
        plan = validate_plan(data,"My name is Alex","auto","mira",["mira"])
        self.assertEqual(plan["facts"],[{"key":"user_name","quote":"My name is Alex"}])
        data["facts"]=[{"key":"../../file","quote":"My name is Alex"}]
        self.assertEqual(validate_plan(data,"My name is Alex","auto","mira",["mira"])["facts"],[])

    def test_empty_reply_fails_instead_of_silent_success(self):
        for data in ([], {}, {"reply":None}, {"reply":"x"*601}):
            with self.assertRaises(ValueError):
                validate_plan(data,"hi","auto","mira",["mira"])

    def test_cloud_is_explicit_and_missing_key_fails_before_network(self):
        with patch.dict(os.environ, {"AI_MATE_LLM_PROVIDER":"minimax","MINIMAX_API_KEY":""}):
            with self.assertRaises(ValueError):
                Conversation("local")
        with patch.dict(os.environ,{"AI_MATE_LLM_PROVIDER":"ollama","AI_MATE_LLM_MODEL":""}):
            self.assertEqual(Conversation("local").provider,"ollama")

    def test_cloudflare_global_key_flow_keeps_credentials_out_of_body(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'.env'
            source.write_text('CLOUDFLARE_ACCOUNT_ID='+'a'*32+'\nCLOUDFLARE_API_KEY=test-secret\nCLOUDFLARE_EMAIL=test@example.test\nUNRELATED_SECRET=ignored\n')
            env = {'AI_MATE_LLM_PROVIDER':'cloudflare','AI_MATE_ENV_FILE':str(source)}
            response = {'choices':[{'message':{'content':json.dumps({'reply':'Hello','action':'none','facts':[]})}}]}
            with patch.dict(os.environ, env, clear=True), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as network:
                model = Conversation('local')
                plan = model.plan({'memory':'','turns':[]},'hello','video','mira',['mira'],threading.Event())
                request = network.call_args.args[0]
                self.assertEqual(request.get_header('X-auth-key'),'test-secret')
                self.assertEqual(request.get_header('X-auth-email'),'test@example.test')
                self.assertIsNone(request.get_header('Authorization'))
                self.assertNotIn(b'test-secret',request.data)
                self.assertNotIn(b'ignored',request.data)
                self.assertEqual(plan['reply'],'Hello')
                self.assertIn('/ai/v1/chat/completions',request.full_url)

    def test_cloudflare_missing_auth_or_invalid_account_never_sends_request(self):
        with patch.dict(os.environ, {'AI_MATE_LLM_PROVIDER':'cloudflare'}, clear=True), patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError): Conversation('local')
            os.environ['CLOUDFLARE_ACCOUNT_ID']='a'*32
            with self.assertRaises(ValueError): Conversation('local')
            os.environ['CLOUDFLARE_ACCOUNT_ID']='../../another-account'
            with self.assertRaises(ValueError): Conversation('local')
            network.assert_not_called()

    def test_fact_correction_reopen_forget_reset_and_prompt_placement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"db"
            store=Store(path)
            store.set_scene("cafe")
            self.assertEqual(Store(path).current_scene(),"cafe")
            store.learn([{"key":"piano_day","quote":"My lesson is Friday"}])
            store.learn([{"key":"piano_day","quote":"My lesson moved to Tuesday"}])
            snapshot=Store(path).snapshot()
            self.assertEqual(len(snapshot["facts"]),1)
            self.assertIn("Tuesday",snapshot["facts"][0]["quote"])
            messages=messages_for(snapshot,"What day?")
            self.assertNotIn("Tuesday",messages[0]["content"])
            self.assertEqual(messages[1]["role"],"user")
            store.forget("piano_day")
            self.assertNotIn("facts",store.snapshot())
            for i in range(20):
                store.learn([{"key":"item_"+str(i),"quote":"Shared fact"}])
            self.assertEqual(len(store.snapshot()["facts"]),12)
            store.reset()
            self.assertNotIn("facts",store.snapshot())
            self.assertEqual(store.current_scene(),"mira")


class StreamTests(unittest.TestCase):
    def test_video_bytes_arrive_before_job_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(directory)
            key="b"*32
            filename=key+"-0.mp4"
            route="/api/streams/"+filename
            file=Path(directory)/filename
            file.write_bytes(b"first")
            app.jobs[key]={"chunks":[{"stream":route}],"state":"rendering","cancel":threading.Event()}
            server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
            server.app=app
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            base=f"http://127.0.0.1:{server.server_port}"
            try:
                request=urllib.request.Request(base+route,headers={"X-Local-Token":app.token})
                with urllib.request.urlopen(request,timeout=3) as response:
                    self.assertEqual(response.read(5),b"first")
                    self.assertEqual(app.jobs[key]["state"],"rendering")
                    with file.open("ab") as sink:sink.write(b"last")
                    app.jobs[key]["state"]="done"
                    self.assertEqual(response.read(),b"last")
                for path,headers,expected in [(route,{},403),("/api/streams/"+"c"*32+"-0.mp4",{"X-Local-Token":app.token},404)]:
                    try:urllib.request.urlopen(urllib.request.Request(base+path,headers=headers))
                    except urllib.error.HTTPError as error:self.assertEqual(error.code,expected)
                    else:self.fail("Private or missing stream unexpectedly accessible")
            finally:
                server.shutdown();server.server_close();worker.join()


if __name__=="__main__":unittest.main()
