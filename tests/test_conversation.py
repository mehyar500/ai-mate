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
    def test_negation_veto_overrides_incorrect_model_action_even_with_asr_punctuation(self):
        for action, prompts in {
            'wave': ["Please do not. Wave, just tell me what you can see.", "Don't wave.", "Don\u2019t raise your hand.", "Never wave.", "Do not move."],
            'closer': ["Come closer. Actually stay there and do not move.", "Do not. Come closer.", "Don't approach me."],
            'farther': ["Please don't step back.", "Never move away.", "Stay where you are."],
        }.items():
            for user in prompts:
                with self.subTest(user=user):
                    data={'reply':'Let me try that.','action':action,'scene':'fullbody','facts':[]}
                    result=validate_plan(data,user,'video','fullbody',['fullbody'])
                    self.assertEqual(result['action'],'none')
                    self.assertEqual(result['reply'],"I'll keep still.")
                    self.assertEqual(result['motion_veto'],'explicit_negation')

    def test_negating_another_action_or_an_unrelated_fact_does_not_block_wave(self):
        data={'reply':'Hello.','action':'wave','scene':'fullbody','facts':[]}
        for user in ["Wave, but do not come closer or step back.", "Don't forget to wave.",
                     "My dog's name is not Pepper. Please wave.", "Wave and stay where you are.", "Don't stop waving."]:
            with self.subTest(user=user):
                result=validate_plan(data,user,'video','fullbody',['fullbody'])
                self.assertEqual(result['action'],'wave')
                self.assertNotIn('motion_veto',result)

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

    def test_video_stop_and_unsupported_hand_correction_are_explicit(self):
        for text in ['Stop.', 'Stop that movement.', 'Hold still.', "Don't move."]:
            plan = direct_motion_plan(text, ['fullbody'])
            self.assertEqual((plan['action'], plan['motion_veto'], plan['decision_source']),
                             ('none', 'stop_command', 'direct_command'))
            self.assertEqual(plan['reply'], "I'll hold still.")
        plan = direct_motion_plan('The other hand.', ['fullbody'])
        self.assertEqual(plan['action'], 'none')
        self.assertEqual(plan['unsupported_motion'], 'other_hand')
        self.assertIn('prepared right-hand', plan['reply'])

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

    def test_suppressed_movement_never_claims_success_in_text_or_voice(self):
        for mode in ['text','voice']:
            for user in ['Wave hello.', 'Could you come closer?', 'Would you step back?']:
                for action in ['none','wave']:
                    data={'reply':'I did that.','action':action,'scene':'fullbody','facts':[]}
                    plan=validate_plan(data,user,mode,'fullbody',['fullbody'])
                    self.assertEqual(plan['action'],'none')
                    self.assertEqual(plan['presentation'],mode)
                    self.assertIn('Switch to Video',plan['reply'])

    def test_nonvisual_motion_hint_preserves_negation_and_conversation(self):
        for user in ['Please do not. Wave.', "Don't come closer."]:
            data={'reply':'I did that.','action':'wave' if 'Wave' in user else 'closer','scene':'fullbody','facts':[]}
            plan=validate_plan(data,user,'voice','fullbody',['fullbody'])
            self.assertEqual(plan['reply'],"I'll keep still.")
        for user in ['Why do people wave hello?', 'Can you describe a wave?', 'I went for a walk.']:
            plan=validate_plan({'reply':'A friendly gesture.','action':'none'},user,'text','fullbody',['fullbody'])
            self.assertEqual(plan['reply'],'A friendly gesture.')

    def test_sparse_plan_keeps_current_state_and_bounded_optional_outputs(self):
        plan=validate_plan({'reply':'Hello'},'Hello','video','fullbody',['fullbody'])
        self.assertEqual(plan,{'reply':'Hello','presentation':'video','scene':'fullbody','action':'none','facts':[]})
        plan=validate_plan({'reply':'Cedar, understood.','facts':[{'key':'dog_name','quote':'Cedar'}]},
                           'My dog is named Cedar.','video','fullbody',['fullbody'])
        self.assertEqual(plan['facts'],[{'key':'dog_name','quote':'Cedar'}])

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
