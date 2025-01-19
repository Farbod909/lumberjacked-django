import datetime
from dateutil import parser
import pytz
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from unittest import mock

from .models import Movement, MovementLog, Workout  # Replace with actual model imports
from authn.models import User

class MovementTests(APITestCase):
    
    @classmethod
    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def setUpTestData(cls):
        cls.user_email = "test@example.com"
        cls.user_password = "password"
        cls.user = User.objects.create_user(email=cls.user_email, password=cls.user_password)
        
        movement_data = {'name': 'Squat', 'category': 'Legs', 'author': cls.user}
        cls.movement = Movement.objects.create(**movement_data)
        
        cls.list_url = reverse('movement-list')
        cls.detail_url = reverse('movement-detail', kwargs={'id': cls.movement.id})

    def setUp(self):
        self.client.login(email=self.user_email, password=self.user_password)

    def tearDown(self):
        self.client.logout()

    def test_authentication_requirements(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.list_url).status_code,
                        status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={'name': 'Bench Press'}).status_code,
                        status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, 
                        status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={'name': 'Squat'}).status_code, 
                        status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(self.detail_url, data={'name': 'Deadlift'}).status_code, 
                        status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 
                        status.HTTP_401_UNAUTHORIZED)

    def test_list_movements(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], "Squat")
        self.assertEqual(response.data['results'][0]['category'], "Legs")
        self.assertEqual(
            parser.isoparse(response.data['results'][0]['created_timestamp']),
            datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc))
        
    def test_list_movements_alt_user(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_create_movement(self):
        movement_data = {'name': 'Bench Press', 'category': 'Chest'}
        response = self.client.post(self.list_url, movement_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(
            any(result['name'] == "Bench Press" for result in response.data['results']))
        self.assertEqual(response.data['results'][0]['author'], self.user.id)
        self.assertEqual(response.data['results'][1]['author'], self.user.id)
        self.assertTrue(
            any(parser.isoparse(result['created_timestamp']) == \
                    datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
                for result in response.data['results'])
        )

    def test_create_movement_missing_required_fields_fails(self):
        movement_data = {'category': 'Chest'}
        response = self.client.post(self.list_url, movement_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_movement(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Squat")
        self.assertEqual(response.data['category'], "Legs")

    def test_retrieve_movement_alt_user_fails(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)
        
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_movement_fails(self):
        url = reverse('movement-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_update_movement(self):
        data = {'name': 'Updated Squat', 'category': 'Updated Legs'}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['name'], "Updated Squat")
        self.assertEqual(response.data['category'], "Updated Legs")
        self.assertEqual(
            parser.isoparse(response.data['updated_timestamp']),
            datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc))
        
    def test_update_missing_required_fields_fails(self):
        data = {'category': 'Updated Legs'}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2022, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_partial_update_movement(self):
        data = {'name': 'Better Squat'}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['name'], "Better Squat")
        self.assertEqual(
            parser.isoparse(response.data['updated_timestamp']),
            datetime.datetime(2022, 3, 12, 0, 0, 0, tzinfo=pytz.utc))
        
    def test_partial_update_missing_required_fields_succeeds(self):
        data = {'category': 'Glutes'}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['category'], "Glutes")

    def test_delete_movement(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

    def test_delete_nonexistent_movement_fails(self):
        url = reverse('movement-detail', kwargs={'id': 123})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
