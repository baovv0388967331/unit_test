import unittest
from unittest.mock import Mock, patch
import csv
import os
from exam import (
    Order,
    APIResponse,
    APIException,
    DatabaseException,
    DatabaseService,
    APIClient,
    OrderProcessingService,
)


class TestOrderProcessingService(unittest.TestCase):
    def setUp(self):
        self.mock_db_service = Mock(spec=DatabaseService)
        self.mock_api_client = Mock(spec=APIClient)
        self.order_processing_service = OrderProcessingService(
            self.mock_db_service, self.mock_api_client
        )

    def tearDown(self):
        # Clean up any created CSV files after each test
        for filename in os.listdir("."):
            if filename.startswith("orders_type_A_") and filename.endswith(".csv"):
                os.remove(filename)

    def test_process_orders_no_orders(self):
        self.mock_db_service.get_orders_by_user.return_value = []
        result = self.order_processing_service.process_orders(1)
        self.assertFalse(result)
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)

    def test_process_orders_type_a_success(self):
        order = Order(1, "A", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "exported")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "exported", "low"
        )

        # Check if CSV file was created
        csv_files = [
            f
            for f in os.listdir(".")
            if f.startswith("orders_type_A_1_") and f.endswith(".csv")
        ]
        self.assertEqual(len(csv_files), 1)
        csv_file = csv_files[0]

        # Check CSV content
        with open(csv_file, "r") as file_handle:
            reader = csv.reader(file_handle)
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[0], ["ID", "Type", "Amount", "Flag", "Status", "Priority"]
            )
            self.assertEqual(rows[1], ["1", "A", "100.0", "false", "exported", "low"])

    def test_process_orders_type_a_high_value(self):
        order = Order(1, "A", 200, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "exported")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "exported", "low"
        )

        # Check if CSV file was created
        csv_files = [
            f
            for f in os.listdir(".")
            if f.startswith("orders_type_A_1_") and f.endswith(".csv")
        ]
        self.assertEqual(len(csv_files), 1)
        csv_file = csv_files[0]

        # Check CSV content
        with open(csv_file, "r") as file_handle:
            reader = csv.reader(file_handle)
            rows = list(reader)
            self.assertEqual(len(rows), 3)
            self.assertEqual(
                rows[0], ["ID", "Type", "Amount", "Flag", "Status", "Priority"]
            )
            self.assertEqual(rows[1], ["1", "A", "200.0", "false", "exported", "low"])
            self.assertEqual(rows[2], ["", "", "", "", "Note", "High value order"])


    def test_process_orders_type_a_failed_export(self):
        order = Order(1, "A", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        # Simulate IOError during file writing
        with patch("builtins.open", side_effect=IOError):
            result = self.order_processing_service.process_orders(1)

        self.assertTrue(result)
        self.assertEqual(order.status, "export_failed")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "export_failed", "low"
        )

    def test_process_orders_type_b_processed(self):
        order = Order(1, "B", 99, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_api_client.call_api.return_value = APIResponse("success", 50)
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "processed")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "processed", "low"
        )

    def test_process_orders_type_b_pending(self):
        order = Order(1, "B", 100, True)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_api_client.call_api.return_value = APIResponse("success", 49)
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "pending", "low"
        )

    def test_process_orders_type_b_error(self):
        order = Order(1, "B", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_api_client.call_api.return_value = APIResponse("success", 50)
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "error")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "error", "low"
        )

    def test_process_orders_type_b_api_error(self):
        order = Order(1, "B", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_api_client.call_api.return_value = APIResponse("failure", None)
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "api_error")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "api_error", "low"
        )

    def test_process_orders_type_b_api_exception(self):
        order = Order(1, "B", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_api_client.call_api.side_effect = APIException
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "api_failure")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "api_failure", "low"
        )

    def test_process_orders_type_c_flag_true(self):
        order = Order(1, "C", 100, True)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "completed")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "completed", "low"
        )

    def test_process_orders_type_c_flag_false(self):
        order = Order(1, "C", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "in_progress")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "in_progress", "low"
        )

    def test_process_orders_unknown_type(self):
        order = Order(1, "D", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "unknown_type")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "unknown_type", "low"
        )

    def test_process_orders_priority_high(self):
        order = Order(1, "A", 201, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.priority, "high")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "exported", "high"
        )

    def test_process_orders_priority_low(self):
        order = Order(1, "A", 200, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "exported", "low"
        )

    def test_process_orders_db_update_failure(self):
        order = Order(1, "A", 100, False)
        self.mock_db_service.get_orders_by_user.return_value = [order]
        self.mock_db_service.update_order_status.side_effect = DatabaseException
        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order.status, "db_error")
        self.assertEqual(order.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_db_service.update_order_status.assert_called_once_with(
            1, "exported", "low"
        )

    def test_process_orders_general_exception(self):
        self.mock_db_service.get_orders_by_user.side_effect = Exception
        result = self.order_processing_service.process_orders(1)
        self.assertFalse(result)
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)

    def test_process_orders_multiple_orders(self):
        order1 = Order(1, "A", 100, False)
        order2 = Order(2, "B", 99, False)
        order3 = Order(3, "C", 100, True)
        self.mock_db_service.get_orders_by_user.return_value = [
            order1,
            order2,
            order3,
        ]
        self.mock_api_client.call_api.return_value = APIResponse("success", 50)
        self.mock_db_service.update_order_status.return_value = True

        result = self.order_processing_service.process_orders(1)
        self.assertTrue(result)
        self.assertEqual(order1.status, "exported")
        self.assertEqual(order2.status, "processed")
        self.assertEqual(order3.status, "completed")
        self.assertEqual(order1.priority, "low")
        self.assertEqual(order2.priority, "low")
        self.assertEqual(order3.priority, "low")
        self.mock_db_service.get_orders_by_user.assert_called_once_with(1)
        self.mock_api_client.call_api.assert_called_once_with(2)
        self.assertEqual(self.mock_db_service.update_order_status.call_count, 3)
        self.mock_db_service.update_order_status.assert_any_call(
            1, "exported", "low"
        )
        self.mock_db_service.update_order_status.assert_any_call(
            2, "processed", "low"
        )
        self.mock_db_service.update_order_status.assert_any_call(
            3, "completed", "low"
        )

    def test_order_initialization(self):
        order = Order(1, "A", 100, True)
        self.assertEqual(order.id, 1)
        self.assertEqual(order.type, "A")
        self.assertEqual(order.amount, 100)
        self.assertEqual(order.flag, True)
        self.assertEqual(order.status, "new")
        self.assertEqual(order.priority, "low")

    def test_api_response_initialization(self):
        response = APIResponse("success", {"data": "some data"})
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"data": "some data"})

    def test_api_exception(self):
        with self.assertRaises(APIException):
            raise APIException

    def test_database_exception(self):
        with self.assertRaises(DatabaseException):
            raise DatabaseException

    def test_database_service_abstract_methods(self):
        with self.assertRaises(TypeError):
            DatabaseService()

    def test_api_client_abstract_methods(self):
        with self.assertRaises(TypeError):
            APIClient()

    def test_order_processing_service_initialization(self):
        self.assertIsNotNone(self.order_processing_service.db_service)
        self.assertIsNotNone(self.order_processing_service.api_client)
