"""Offline pose flags retain uncertainty and detect injected discontinuities."""
import copy
import unittest
from types import SimpleNamespace

from scripts.review_body_motion import inspect_frame, landmark_metrics


def standing():
    points=[[50,10,0,1,1] for _ in range(33)]
    for i,x,y in [(11,40,30),(12,60,30),(13,35,50),(14,65,50),
                  (15,30,70),(16,70,70),(23,43,65),(24,57,65),
                  (25,43,90),(26,57,90),(27,43,115),(28,57,115)]:
        points[i][:2]=[x,y]
    return points


class BodyMetricsTests(unittest.TestCase):
    def test_missing_or_multiple_people_cannot_be_reported_as_valid_motion(self):
        image=SimpleNamespace(shape=(130,100,3))
        for people in ([], [[0],[1]]):
            detector=SimpleNamespace(infer=lambda image:people)
            result=inspect_frame(image,detector,None)
            self.assertIn('person_count',result['flags'])
            self.assertNotIn('raised',result)

    def test_missing_pose_keeps_uncertainty_instead_of_reusing_previous_joints(self):
        image=SimpleNamespace(shape=(130,100,3))
        detector=SimpleNamespace(infer=lambda image:[[0]])
        pose=SimpleNamespace(infer=lambda image,person:None)
        previous=landmark_metrics(standing(),100,130)
        result=inspect_frame(image,detector,pose,previous)
        self.assertEqual(result['flags'],['missing_pose'])
        self.assertNotIn('joints',result)

    def test_right_raise_does_not_claim_left_raise(self):
        points=standing();points[16][1]=20
        result=landmark_metrics(points,100,130)
        self.assertEqual(result['raised'],{'left':False,'right':True})

    def test_occluded_or_out_of_frame_wrist_is_unknown(self):
        points=standing();points[16][1]=20;points[16][3]=.1
        self.assertIsNone(landmark_metrics(points,100,130)['raised']['right'])
        points[16][3]=1;points[16][0]=110
        self.assertIsNone(landmark_metrics(points,100,130)['raised']['right'])

    def test_small_movement_is_retained_and_large_jump_is_flagged(self):
        points=standing();previous=landmark_metrics(points,100,130)
        moved=copy.deepcopy(points);moved[16][0]+=1
        self.assertEqual(landmark_metrics(moved,100,130,previous)['flags'],[])
        moved[16][1]=15
        result=landmark_metrics(moved,100,130,previous)
        self.assertIn('landmark_jump',result['flags'])
        self.assertGreater(result['max_joint_step_torsos'],.75)

    def test_torso_uncertainty_and_bad_model_output_are_not_a_pass(self):
        points=standing();points[23][4]=.1
        self.assertIn('uncertain_torso',landmark_metrics(points,100,130)['flags'])
        points[23][0]=float('nan')
        with self.assertRaises(ValueError):landmark_metrics(points,100,130)
        with self.assertRaises(ValueError):landmark_metrics([],100,130)


if __name__ == '__main__':
    unittest.main()
