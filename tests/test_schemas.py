import unittest

from models.schemas import ParsedResume, parse_model


class SchemaTests(unittest.TestCase):
    def test_parse_model_returns_valid_model_for_json(self):
        parsed = parse_model(
            ParsedResume,
            '{"name": "Asha", "email": "asha@example.com", "skills": ["Python"], "experience_years": 2, "projects": []}',
            ParsedResume(),
        )

        self.assertEqual(parsed.name, "Asha")
        self.assertEqual(parsed.email, "asha@example.com")
        self.assertEqual(parsed.skills, ["Python"])

    def test_parse_model_uses_fallback_for_invalid_json(self):
        fallback = ParsedResume(name="Unknown")

        parsed = parse_model(ParsedResume, "not json", fallback)

        self.assertEqual(parsed.name, "Unknown")


if __name__ == "__main__":
    unittest.main()
