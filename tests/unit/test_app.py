import unittest
from unittest import TestCase, mock
import urllib.parse

from upload_function.app import parse_s3_object_url, parse_pathname, clean_result, s3_location

GOOD_ENCODED_PATHNAME: str = "1/81ccea53-9d35-4acf-8cdb-883dfe22e9e9/273acbe3-c937-496e-86f8-f5a0166843c3/" \
                             "2022-07-08%20Grant%20Application%20Definition%20-%20Definition%20-" \
                             "%20Grant%20applicant%20Programme%20-%20Confluence.pdf"
GOOD_HTTP_ENCODED_LOCATION: str = "https://gap-sandbox-uploads.s3.eu-west-2.amazonaws.com/" + GOOD_ENCODED_PATHNAME
GOOD_S3_ENCODED_LOCATION: str = "s3://gap-sandbox-uploads.s3.eu-west-2.amazonaws.com/" + GOOD_ENCODED_PATHNAME

GOOD_PATHNAME: str = "1/81ccea53-9d35-4acf-8cdb-883dfe22e9e9/273acbe3-c937-496e-86f8-f5a0166843c3/simple.doc"
GOOD_HTTP_LOCATION: str = "https://gap-sandbox-uploads.s3.eu-west-2.amazonaws.com/" + GOOD_PATHNAME


class LocationParsingTestCases(TestCase):

    def test_returns_empty_for_blank_input(self):
        result = parse_s3_object_url("")
        self.assertEqual(result, "")

    def test_can_parse_expected_http_encoded_location(self):
        result = parse_s3_object_url(GOOD_HTTP_ENCODED_LOCATION)
        expected = urllib.parse.unquote_plus(GOOD_ENCODED_PATHNAME)
        self.assertEqual(result, expected)

    def test_can_parse_expected_http_location(self):
        result = parse_s3_object_url(GOOD_HTTP_LOCATION)
        self.assertEqual(result, GOOD_PATHNAME)

    def test_can_parse_expected_s3_encoded_location(self):
        result = parse_s3_object_url(GOOD_S3_ENCODED_LOCATION)
        expected = urllib.parse.unquote_plus(GOOD_ENCODED_PATHNAME)
        self.assertEqual(result, expected)


class PathnameParsingTestCases(TestCase):

    SUBSCRIPTION_ID = "subscriptionId"
    QUESTION_ID = "questionId"
    PATH = "1/" + SUBSCRIPTION_ID + "/" + QUESTION_ID + "/filename"

    def test_returns_empty_for_blank_input(self):
        subscription_id, question_id = parse_pathname("")
        self.assertEqual(subscription_id, "")
        self.assertEqual(question_id, "")

    def test_returns_empty_for_malformed_input(self):
        subscription_id, question_id = parse_pathname("not an expected path")
        self.assertEqual(subscription_id, "")
        self.assertEqual(question_id, "")

    def test_returns_empty_for_short_input(self):
        subscription_id, question_id = parse_pathname("1/2/filename")
        self.assertEqual(subscription_id, "")
        self.assertEqual(question_id, "")

    def test_returns_expected_values_for_good_input(self):
        subscription_id, question_id = parse_pathname(self.PATH)
        self.assertEqual(subscription_id, self.SUBSCRIPTION_ID)
        self.assertEqual(question_id, self.QUESTION_ID)


class CleanResultTestCases(TestCase):

    def test_with_missing_result_returns_false(self):
        message = {"element": "value"}
        result = clean_result(message)
        self.assertFalse(result)

    def test_with_scan_result_findings_returns_false(self):
        message = {"scanning_result": {"Findings": "bad things"}}
        result = clean_result(message)
        self.assertFalse(result)

    def test_with_no_findings_returns_true(self):
        message = {"scanning_result": {}}
        result = clean_result(message)
        self.assertTrue(result)


# need to patch the global values in app - can't patch environ calls for these
@mock.patch("upload_function.app.CLEAN_BUCKET", new="good")
@mock.patch("upload_function.app.QUARANTINE_BUCKET", new="bad")
class S3LocationTests(TestCase):

    def test_clean_result_location_will_include_clean_bucket(self):
        location = s3_location(True, "path")
        self.assertIn("good", location)

    def test_not_clean_result_location_will_include_quarantine_bucket(self):
        location = s3_location(False, "path")
        self.assertIn("bad", location)


if __name__ == '__main__':
    unittest.main()
