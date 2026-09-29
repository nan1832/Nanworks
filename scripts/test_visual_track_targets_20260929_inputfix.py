"""Check causal alignment and equal sample weighting without loading any VLM."""
import types
import unittest
from run_visual_track_targets_20260929_inputfix import answer_layout, equal_sample_mean, append_answer, capture

class LayoutTests(unittest.TestCase):
    def test_answer_shift_and_special_token_exclusion(self):
        layout=answer_layout(5,[11,12,2],[0,1,2])
        self.assertEqual(layout['prediction_positions'],[4,5])
        self.assertEqual(layout['read_positions'],[5,6])
        self.assertEqual(layout['excluded_special_tokens'],1)
    def test_long_answers_do_not_get_more_sample_weight(self):
        self.assertAlmostEqual(equal_sample_mean([[1.],[-1.]*100]),0.)
    def test_empty_answers_fail(self):
        with self.assertRaises(ValueError):answer_layout(5,[1,2],[1,2])

class CausalTests(unittest.TestCase):
    def test_preencoded_image_placeholders_only(self):
        import torch
        embedding=torch.nn.Embedding(30,8)
        inputs={'inputs_embeds':embedding(torch.tensor([[1,2,3]])),
                'pixel_values':None,'pixel_attention_mask':None}
        result=append_answer(inputs,[11,12],embedding)
        self.assertIsNone(result['pixel_values'])
        self.assertIsNone(result['pixel_attention_mask'])
        self.assertTrue(torch.equal(result['inputs_embeds'][:,:3],inputs['inputs_embeds']))
        self.assertEqual(inputs['inputs_embeds'].shape[1],3)
        for name in ('pixel_values','pixel_attention_mask'):
            with self.assertRaisesRegex(AssertionError,'Image must be encoded'):
                append_answer(dict(inputs,**{name:torch.ones(1)}),[11],embedding)
        with self.assertRaisesRegex(AssertionError,'Audit new model input fields'):
            append_answer(dict(inputs,unreviewed_field=None),[11],embedding)

    def test_full_answer_prefix_and_single_token_degeneracy(self):
        import torch
        torch.manual_seed(1)
        class CausalBlock(torch.nn.Module):
            def forward(self,x):
                return x.cumsum(1)/torch.arange(1,x.shape[1]+1)[None,:,None]
        block=CausalBlock();embedding=torch.nn.Embedding(30,8)
        helper=types.SimpleNamespace(tensor_from_layer_output=lambda x:x)
        class Model:
            def get_llm_outpt(self,inputs,vt):return block(inputs['inputs_embeds'])
        model=Model();prefix=embedding(torch.tensor([[1,2,3,4,5]])).detach()
        original={'inputs_embeds':prefix,'attention_mask':torch.ones((1,5),dtype=torch.long),'input_ids':torch.tensor([[1,2,3,4,5]]),'position_ids':torch.arange(1,6)[None,:]}
        baseline=capture(model,helper,{0:block},original,[0,2],{'prediction_positions':[4]})[0]
        values=[]
        for ids in [[11],[20],[11,12,13],[20,21,22]]:
            inputs=append_answer(original,ids,embedding)
            self.assertTrue(torch.equal(inputs['inputs_embeds'][:,:5],prefix))
            self.assertEqual(inputs['position_ids'].tolist(),[list(range(1,6+len(ids)))])
            layout=answer_layout(5,ids,[0])
            r=capture(model,helper,{0:block},inputs,[0,2],layout)[0]
            self.assertAlmostEqual(r['first_predict_cos'],baseline['visual_track_cos'],places=6)
            h=block(inputs['inputs_embeds'])[0];v=h[:2].mean(0)
            direct=torch.nn.functional.cosine_similarity(v[None,:],h[layout['prediction_positions']],dim=-1).mean().item()
            self.assertAlmostEqual(r['visual_track_cos'],direct,places=6)
            values.append(r)
        self.assertAlmostEqual(values[0]['visual_track_cos'],values[1]['visual_track_cos'],places=6)
        self.assertNotAlmostEqual(values[0]['answer_read_cos'],values[1]['answer_read_cos'],places=4)
        self.assertNotAlmostEqual(values[2]['visual_track_cos'],values[3]['visual_track_cos'],places=4)
        self.assertEqual(len(block._forward_hooks),0)

if __name__=='__main__':unittest.main()
