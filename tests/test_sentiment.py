"""Focused checks for Verity's current rule-based sentiment behavior.

Run from the Verity repository root: python tests/test_sentiment.py
Only the reviewed pure function and its constant word sets are loaded; the
Flask application, browser collection, and network services are not started.
These examples do not establish classification accuracy on real-world data.
"""
import ast
from pathlib import Path
import re
import unittest

source_path = Path(__file__).resolve().parents[1] / 'backend' / 'app.py'
tree = ast.parse(source_path.read_text(encoding='utf-8'))
constant_names = {'POSITIVE_WORDS', 'NEGATIVE_WORDS', 'NEGATION_WORDS'}
selected = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constant_names for t in node.targets):
        selected.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name == 'analyze_sentiment':
        selected.append(node)
namespace = {'re': re}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(source_path), 'exec'), namespace)
analyze_sentiment = namespace['analyze_sentiment']

class SentimentBehaviorChecks(unittest.TestCase):
    def test_positive(self): self.assertEqual(analyze_sentiment('Excellent friendly service')['label'], 'Positive')
    def test_negative(self): self.assertEqual(analyze_sentiment('Terrible rude service')['label'], 'Negative')
    def test_neutral(self): self.assertEqual(analyze_sentiment('A table near the window')['label'], 'Neutral')
    def test_mixed(self): self.assertEqual(analyze_sentiment('Good food but bad service')['label'], 'Mixed')
    def test_negated_positive(self): self.assertEqual(analyze_sentiment('not good')['label'], 'Negative')
    def test_negated_negative(self): self.assertEqual(analyze_sentiment('not bad')['label'], 'Positive')
    def test_case_and_punctuation(self): self.assertEqual(analyze_sentiment('GREAT!!!')['label'], 'Positive')
    def test_empty(self): self.assertEqual(analyze_sentiment('')['label'], 'Neutral')

if __name__ == '__main__': unittest.main()
