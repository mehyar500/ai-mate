import json
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from local_app.conversation import Conversation, validate_plan, direct_motion_plan
from local_app.core import Store, messages_for
from local_app.server import Application, Handler, ThreadingHTTPServer


class PlanTests(unittest.TestCase):
    def test_scene_mentions_preserve_current_view_but_visual_requests_can_change_it(self):
        available=['mira','garden','cafe','fullbody']
        data={'reply':'The garden is peaceful.','presentation':'video','scene':'garden','action':'none','facts':[]}
        for text in ['Describe a peaceful walk in this garden in two sentences.',
                     'Tell me about the garden.', "Don't go to the garden.",
                     'Could you describe the garden?', 'I remember the garden.']:
            self.assertEqual(validate_plan(data,text,'video','fullbody',available)['scene'],'fullbody')
        for text in ["Let's go to the garden.", 'Please show me the garden.',
                     'Could you show me the garden?', 'Take me there.', "Let's go there.",
                     'Back to the garden.', 'Show me.', 'Send a video from there.']:
            self.assertEqual(validate_plan(data,text,'video','mira',available)['scene'],'garden')
        for text in ['Show me your full body.', 'Please stand up.', 'Come closer.']:
            self.assertEqual(validate_plan({**data,'scene':'fullbody'},text,'video','garden',available)['scene'],'fullbody')
        self.assertEqual(validate_plan({**data,'scene':'cafe'},"Let's go to the coffee shop.",'video','garden',available)['scene'],'cafe')
        self.assertEqual(validate_plan({**data,'scene':'cafe'},"Let's talk in the café.",'video','garden',available)['scene'],'cafe')

    def test_unrequested_stale_action_is_discarded_but_contextual_repeat_is_allowed(self):
        data={'reply':'The garden is peaceful.','presentation':'video','scene':'fullbody','action':'wave','facts':[]}
        for text in ['Tell me two sentences about a peaceful walk in the garden.', 'How are you?', 'What were we discussing?']:
            self.assertEqual(validate_plan(data,text,'video','fullbody',['fullbody'])['action'],'none')
        self.assertEqual(validate_plan(data,'Do that again.','video','fullbody',['fullbody'])['action'],'wave')

    def test_selected_mode_cannot_be_overridden_by_model_or_body_command(self):
        for mode in ['text','voice','video']:
            plan=validate_plan({'reply':'Okay','presentation':'video','action':'wave','scene':'fullbody','facts':[]},
                               'Wave',mode,'mira',['mira','fullbody'])
            self.assertEqual(plan['presentation'],mode)
            self.assertEqual(plan['action'],'wave' if mode=='video' else 'none')

    def test_call_message_is_bounded_and_does_not_change_call(self):
        data={'reply':'Sent it to Text.','presentation':'text','message':'Meet me here tomorrow.','facts':[]}
        plan=validate_plan(data,'Send me a message','video','mira',['mira'])
        self.assertEqual(plan['presentation'],'video')
        self.assertEqual(plan['message'],data['message'])
        for invalid in ['', 'x'*601, {}, None]:
            self.assertNotIn('message',validate_plan({**data,'message':invalid},'hi','voice','mira',['mira']))
        self.assertNotIn('message',validate_plan(data,'hi','text','mira',['mira']))

    def test_direct_commands_bypass_network_but_context_and_negations_do_not(self):
        with patch.dict(os.environ, {'AI_MATE_LLM_PROVIDER':'ollama'},clear=True), patch('urllib.request.urlopen') as network:
            model=Conversation('local')
            plan=model.plan({'memory':'','turns':[]},'Raise your hand and say hello briefly.','video','fullbody',['fullbody'],threading.Event())
            self.assertEqual((plan['action'],plan['reply'],plan['decision_source']),('wave','Hello.','direct_command'))
            network.assert_not_called()
        for text in ["Don't wave",'Wave if you remember my name','Come closer and tell me about yesterday',
                     'What does wave mean?', 'Raise your hand but do not move']:
            self.assertIsNone(direct_motion_plan(text,['fullbody']))
        self.assertIsNone(direct_motion_plan('Wave hello',['mira']))

    def test_explicit_repeat_motion_is_not_lost_to_none_action(self):
        data={'reply':'Hello','presentation':'continue','scene':'keep','action':'none','facts':[]}
        for text, expected in [('Raise your hand and say hello.','wave'),('Come closer.','closer'),('Step back.','farther')]:
            plan=validate_plan(data,text,'video','mira',['mira','fullbody'])
            self.assertEqual((plan['action'],plan['presentation'],plan['scene']),(expected,'video','fullbody'))
        for text in ["Don't wave.", 'What does wave mean?', 'Please do not come closer.']:
            self.assertEqual(validate_plan(data,text,'video','mira',['mira','fullbody'])['action'],'none')

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
            env = {'AI_MATE_LLM_PROVIDER':'cloudflare','AI_MATE_ENV_FILE':str(source), 'CLOUDFLARE_API_TOKEN':'stale-token'}
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

    def test_cloudflare_key_without_email_does_not_fall_back_to_token(self):
        env = {'AI_MATE_LLM_PROVIDER':'cloudflare', 'CLOUDFLARE_ACCOUNT_ID':'a'*32,
               'CLOUDFLARE_API_KEY':'test-secret', 'CLOUDFLARE_API_TOKEN':'stale-token'}
        with patch.dict(os.environ, env, clear=True), patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(ValueError, 'CLOUDFLARE_EMAIL'):
                Conversation('local')
            network.assert_not_called()

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
