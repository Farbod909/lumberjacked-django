import datetime
from dateutil import parser
from django.urls import reverse
from django.utils import timezone
import pytz
from rest_framework.test import APITestCase
from rest_framework import status
from unittest import mock
from urllib.parse import urlencode

from .models import Movement, MovementLog, Workout
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

    def test_delete_movement_with_movement_logs(self):
        workout = Workout.objects.create(user=self.user, movements=[self.movement.id])
        MovementLog.objects.create(
            movement=self.movement, workout=workout, reps=[5, 5, 5], loads=[25, 25, 25])
        self.assertEqual(MovementLog.objects.count(), 1)
        
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertEqual(MovementLog.objects.count(), 0)

class WorkoutTests(APITestCase):

    @classmethod
    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def setUpTestData(cls):
        cls.user_email = "test@example.com"
        cls.user_password = "password"
        cls.user = User.objects.create_user(email=cls.user_email, password=cls.user_password)

        cls.movement1 = Movement.objects.create(name="Squat", category="Legs", author=cls.user)
        cls.movement2 = Movement.objects.create(name="Bench Press", category="Chest", author=cls.user)

        workout_data = {
            'user': cls.user,
            'movements': [cls.movement1.id, cls.movement2.id],
        }
        cls.workout = Workout.objects.create(**workout_data)

        cls.list_url = reverse('workout-list')
        cls.create_url_with_template = f"{reverse('workout-list')}?{urlencode({'template': cls.workout.id})}"
        cls.detail_url = reverse('workout-detail', kwargs={'id': cls.workout.id})
        cls.end_url = reverse('workout-end', kwargs={'id': cls.workout.id})
        cls.current_url = reverse('workout-current')

    def setUp(self):
        self.client.login(email=self.user_email, password=self.user_password)

    def tearDown(self):
        self.client.logout()

    def test_authentication_requirements(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.end_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_workouts(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)
        self.assertListEqual(
            [movement['id'] for movement in response.data['results'][0]['movements_details']],
            [self.movement1.id, self.movement2.id])
        
    def test_list_workouts_alt_user(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_create_workout_with_movements(self):
        workout_data = {
            'movements': [self.movement1.id],
        }
        response = self.client.post(self.list_url, workout_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(any(
            [movement['id'] for movement in workout['movements_details']] == [self.movement1.id]
            for workout in response.data['results']
        ))

    def test_retrieve_workout_alt_user_fails(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)
        
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_workout_fails(self):
        url = reverse('workout-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_workout(self):
        data = {
            'movements': [self.movement1.id],
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertListEqual(
            [movement['id'] for movement in response.data['movements_details']],
            [self.movement1.id])

    def test_delete_workout(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

    def test_delete_nonexistent_workout_fails(self):
        url = reverse('workout-detail', kwargs={'id': 123})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_workout_with_movement_logs(self):
        MovementLog.objects.create(
            movement=self.movement1, workout=self.workout, reps=[5, 5, 5], loads=[25, 25, 25])
        self.assertEqual(MovementLog.objects.count(), 1)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(MovementLog.objects.count(), 0)


    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2022, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_end_workout(self):
        response = self.client.get(self.end_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(parser.isoparse(response.data['end_timestamp']), 
                         datetime.datetime(2022, 3, 12, 0, 0, 0, tzinfo=pytz.utc))

    def test_end_nonexistent_workout_fails(self):
        url = reverse('workout-end', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_current_workout(self):
        self.client.get(self.end_url) # end existing workout

        self.movement3 = Movement.objects.create(name="Pullup", category="Back", author=self.user)
        self.current_workout = Workout.objects.create(user=self.user, movements=[self.movement2.id, self.movement3.id])

        MovementLog.objects.create(
            movement=self.movement1,
            workout=self.workout, 
            reps=[5, 5, 5], 
            loads=[25, 25, 25], 
            timestamp=timezone.now() - datetime.timedelta(seconds=15))
        MovementLog.objects.create(
            movement=self.movement2,
            workout=self.workout,
            reps=[8, 8, 8],
            loads=[120, 120, 120],
            timestamp=timezone.now() - datetime.timedelta(seconds=10))
        MovementLog.objects.create(
            movement=self.movement2,
            workout=self.current_workout,
            reps=[10, 10, 10],
            loads=[130, 130, 130],
            timestamp=timezone.now() - datetime.timedelta(seconds=5))
        MovementLog.objects.create(
            movement=self.movement3,
            workout=self.current_workout,
            reps=[5, 5, 5],
            loads=[200, 200, 200],
            timestamp=timezone.now())
        
        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['movements_details']), 2)

        self.assertTrue(any(details['name'] == "Pullup" for details in response.data['movements_details']))
        self.assertTrue(any(details['name'] == "Bench Press" for details in response.data['movements_details']))

        self.assertTrue(all(details['latest_log']['for_current_workout'] == True for details in response.data['movements_details']))


    def test_current_workout_half_complete(self):
        self.client.get(self.end_url) # end existing workout

        self.movement3 = Movement.objects.create(name="Pullup", category="Back", author=self.user)
        self.current_workout = Workout.objects.create(user=self.user, movements=[self.movement2.id, self.movement3.id])

        MovementLog.objects.create(
            movement=self.movement1,
            workout=self.workout,
            reps=[5, 5, 5],
            loads=[25, 25, 25],
            timestamp=timezone.now() - datetime.timedelta(seconds=10))
        MovementLog.objects.create(
            movement=self.movement2,
            workout=self.workout,
            reps=[8, 8, 8],
            loads=[130, 130, 130],
            timestamp=timezone.now() - datetime.timedelta(seconds=5))
        MovementLog.objects.create(
            movement=self.movement3,
            workout=self.current_workout,
            reps=[5, 5, 5],
            loads=[200, 200, 200],
            timestamp=timezone.now())
        
        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['movements_details']), 2)

        self.assertTrue(any(details['name'] == "Pullup" for details in response.data['movements_details']))
        self.assertTrue(any(details['name'] == "Bench Press" for details in response.data['movements_details']))

        self.assertTrue(any(details['latest_log']['for_current_workout'] == False for details in response.data['movements_details']))

    def test_current_workout_nonexistent_fails(self):
        self.client.get(self.end_url) # end existing workout
        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class MovementLogTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        mock_now = datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
        # Override the `default` callable for the timestamp field to ensure the mock is used.
        with mock.patch('django.utils.timezone.now', return_value=mock_now):
            MovementLog._meta.get_field('timestamp').default = timezone.now

            cls.user_email = "test@example.com"
            cls.user_password = "password"
            cls.user = User.objects.create_user(email=cls.user_email, password=cls.user_password)

            cls.movement1 = Movement.objects.create(name="Squat", category="Legs", author=cls.user)
            cls.movement2 = Movement.objects.create(name="Bench Press", category="Chest", author=cls.user)

            cls.workout1 = Workout.objects.create(user=cls.user, movements=[cls.movement1.id])
            cls.workout2 = Workout.objects.create(user=cls.user, movements=[cls.movement2.id])

            cls.movement1_log1 = MovementLog.objects.create(
                movement=cls.movement1, workout=cls.workout1, reps=[5, 5, 5], loads=[25, 25, 25])
            cls.movement2_log1 = MovementLog.objects.create(
                movement=cls.movement2, workout=cls.workout2, reps=[8, 8, 8], loads=[130, 130, 130])
            cls.movement2_log2 = MovementLog.objects.create(
                movement=cls.movement2, workout=cls.workout2, reps=[10, 10, 10], loads=[130, 130, 135])
            cls.movement2_log3 = MovementLog.objects.create(
                movement=cls.movement2, workout=cls.workout2, reps=[9, 9, 9], loads=[135, 135, 135])
        
        cls.list_url = reverse('movement-log-list')
        cls.list_url_with_movement = f"{reverse('movement-log-list')}?{urlencode({'movement': cls.movement1.id})}"
        cls.list_url_with_workout = f"{reverse('movement-log-list')}?{urlencode({'workout': cls.workout1.id})}"
        cls.list_url_with_workout_include_recent_logs = \
            f"{reverse('movement-log-list')}?{urlencode({'workout': cls.workout1.id})}" + \
            f"&{urlencode({'include-recent-logs': 1})}"
        cls.detail_url = reverse('movement-log-detail', kwargs={'id': cls.movement1_log1.id})


    def setUp(self):
        self.client.login(email=self.user_email, password=self.user_password)

    def tearDown(self):
        self.client.logout()

    def test_authentication_requirements(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movement_logs(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        response_movement_log_movement_ids = [log['movement_detail']['id'] for log in response.data['results']]
        expected_movement_log_movement_ids = [self.movement1.id, self.movement2.id, self.movement2.id, self.movement2.id]
        self.assertCountEqual(response_movement_log_movement_ids, expected_movement_log_movement_ids)

    def test_list_movement_logs_alt_user(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_list_movement_logs_with_movement(self):
        response = self.client.get(self.list_url_with_movement)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['movement_detail']['id'], self.movement1.id)

    def test_list_movement_logs_with_workout(self):
        response = self.client.get(self.list_url_with_workout)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['workout'], self.workout1.id)

    @mock.patch('django.utils.timezone.now',
            mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_create_movement_log(self):
        movement_log_data = {'movement': self.movement2.id, 'workout': self.workout2.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 5)
        self.assertTrue(
            any(result['reps'] == [3, 2, 1] for result in response.data['results']))
        self.assertTrue(
            any(parser.isoparse(result['timestamp']) == \
                    datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
                for result in response.data['results'])
        )

    def test_create_movement_log_missing_workout_field_fails(self):
        movement_log_data = {'workout': self.workout2.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_movement_log_missing_workout_field_fails(self):
        movement_log_data = {'movement': self.movement2.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_invalid_movement_field_fails(self):
        movement_log_data = {'movement': 123, 'workout': self.workout2.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_invalid_workout_field_fails(self):
        movement_log_data = {'movement': self.movement2.id, 'workout': 123, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_not_owning_movement_fails(self):
        alt_user_email = "alt@example.com"
        alt_user_password = "altpassword"
        alt_user = User.objects.create_user(
            email=alt_user_email, password=alt_user_password)
        alt_user_movement = Movement.objects.create(name="Deadlift", category="Core", author=alt_user)

        movement_log_data = {'movement': alt_user_movement.id, 'workout': self.workout2.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movement_log_not_owning_workout_fails(self):
        alt_user_email = "alt@example.com"
        alt_user_password = "altpassword"
        alt_user = User.objects.create_user(
            email=alt_user_email, password=alt_user_password)
        alt_user_workout = Workout.objects.create(user=alt_user)

        movement_log_data = {'movement': self.movement2.id, 'workout': alt_user_workout.id, 'reps': [3, 2, 1], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movement_log_reps_and_loads_length_mismatch_fails(self):
        movement_log_data = {'movement': self.movement2.id, 'workout': self.workout2.id, 'reps': [3, 2], 'loads': [123, 456, 789]}
        response = self.client.post(self.list_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_movement_log(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reps'], [5, 5, 5])

    def test_retrieve_nonexistent_movement_log_fails(self):
        url = reverse('movement-log-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_movement_log_alt_user(self):
        self.client.logout()
        self.alt_user_email = "alt@example.com"
        self.alt_user_password = "altpassword"
        self.alt_user = User.objects.create_user(
            email=self.alt_user_email, password=self.alt_user_password)
        self.client.login(email=self.alt_user_email, password=self.alt_user_password)
        
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('django.utils.timezone.now',
            mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_update_movement_log(self):
        data = {'movement': self.movement2.id, 'workout': self.workout2.id, 'reps': [1], 'loads': [2]}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['movement_detail']['id'], self.movement2.id)
        self.assertEqual(response.data['workout'], self.workout2.id)
        self.assertEqual(response.data['reps'], [1])
        self.assertEqual(response.data['loads'], [2])
        self.assertEqual( # assert timestamp is unchanged
            parser.isoparse(response.data['timestamp']),
            datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc))

    def test_update_movement_log_timestamp(self):
        data = {'timestamp': datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc).isoformat()}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(
            parser.isoparse(response.data['timestamp']),
            datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc))

    def test_update_movement_log_not_owning_movement_fails(self):
        alt_user_email = "alt@example.com"
        alt_user_password = "altpassword"
        alt_user = User.objects.create_user(
            email=alt_user_email, password=alt_user_password)
        alt_user_movement = Movement.objects.create(name="Deadlift", category="Core", author=alt_user)

        data = {'movement': alt_user_movement.id, 'workout': self.workout2.id, 'reps': [1], 'loads': [2]}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movement_log_not_owning_workout_fails(self):
        alt_user_email = "alt@example.com"
        alt_user_password = "altpassword"
        alt_user = User.objects.create_user(
            email=alt_user_email, password=alt_user_password)
        alt_user_workout = Workout.objects.create(user=alt_user)

        data = {'movement': self.movement2.id, 'workout': alt_user_workout.id, 'reps': [1], 'loads': [2]}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_update_movement_log_reps_and_loads_length_mismatch_fails(self):
        movement_log_data = {'reps': [3, 2], 'loads': [123, 456, 789]}
        response = self.client.patch(self.detail_url, movement_log_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_movement_log(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 3)

    def test_delete_nonexistent_movement_log_fails(self):
        url = reverse('movement-log-detail', kwargs={'id': 123})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)