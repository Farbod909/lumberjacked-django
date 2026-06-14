import datetime
from dateutil import parser
from django.urls import reverse
from django.utils import timezone
import pytz
from rest_framework.test import APITestCase
from rest_framework import status
from unittest import mock
from urllib.parse import urlencode

from .models import Movement, MovementLog, MovementLogTemplate, Workout, WorkoutMovement, WorkoutTemplate, WorkoutTemplateMovement
from authn.models import User


class MovementTests(APITestCase):

    @classmethod
    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="test@example.com", password="password")

        movement_data = {'name': 'Squat', 'author': cls.user}
        cls.movement = Movement.objects.create(**movement_data)

        cls.list_url = reverse('movement-list')
        cls.detail_url = reverse('movement-detail', kwargs={'id': cls.movement.id})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    def test_authentication_requirements(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={'name': 'Bench Press'}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={'name': 'Squat'}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(self.detail_url, data={'name': 'Deadlift'}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movements(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], "Squat")
        self.assertEqual(
            parser.isoparse(response.data['results'][0]['created_timestamp']),
            datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc))

    def test_list_movements_alt_user(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_create_movement(self):
        movement_data = {'name': 'Bench Press'}
        response = self.client.post(self.list_url, movement_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(any(result['name'] == "Bench Press" for result in response.data['results']))
        self.assertEqual(response.data['results'][0]['author'], self.user.id)
        self.assertEqual(response.data['results'][1]['author'], self.user.id)
        self.assertTrue(
            any(parser.isoparse(result['created_timestamp']) ==
                    datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
                for result in response.data['results'])
        )

    def test_create_movement_missing_required_fields_fails(self):
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_movement(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Squat")

    def test_retrieve_movement_alt_user_fails(self):
        alt_user = User.objects.create_user(email="alt2@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_movement_fails(self):
        url = reverse('movement-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_update_movement(self):
        data = {'name': 'Updated Squat'}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['name'], "Updated Squat")
        self.assertEqual(
            parser.isoparse(response.data['updated_timestamp']),
            datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc))

    def test_update_missing_required_fields_fails(self):
        response = self.client.put(self.detail_url, {})
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
        data = {'notes': 'Keep back straight'}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['notes'], 'Keep back straight')

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
        workout = Workout.objects.create(user=self.user)
        wm = WorkoutMovement.objects.create(workout=workout, movement=self.movement, order=0)
        MovementLog.objects.create(
            workout_movement=wm,
            sets=[{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}])
        self.assertEqual(MovementLog.objects.count(), 1)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(MovementLog.objects.count(), 0)


class WorkoutTests(APITestCase):

    @classmethod
    @mock.patch('django.utils.timezone.now',
                mock.Mock(return_value=datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="test@example.com", password="password")

        cls.movement1 = Movement.objects.create(name="Squat", author=cls.user)
        cls.movement2 = Movement.objects.create(name="Bench Press", author=cls.user)

        cls.workout = Workout.objects.create(user=cls.user)
        WorkoutMovement.objects.create(workout=cls.workout, movement=cls.movement1, order=0)
        WorkoutMovement.objects.create(workout=cls.workout, movement=cls.movement2, order=1)

        cls.list_url = reverse('workout-list')
        cls.detail_url = reverse('workout-detail', kwargs={'id': cls.workout.id})
        cls.end_url = reverse('workout-end', kwargs={'id': cls.workout.id})
        cls.current_url = reverse('workout-current')

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    def test_authentication_requirements(self):
        self.client.force_authenticate(user=None)
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
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_create_workout_with_movements(self):
        workout_data = {'movements': [self.movement1.id]}
        response = self.client.post(self.list_url, workout_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(any(
            [movement['id'] for movement in workout['movements_details']] == [self.movement1.id]
            for workout in response.data['results']
        ))

    def test_retrieve_workout_alt_user_fails(self):
        alt_user = User.objects.create_user(email="alt2@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_workout_fails(self):
        url = reverse('workout-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_workout(self):
        data = {'movements': [self.movement1.id]}
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
        wm = self.workout.workout_movements.filter(movement=self.movement1).first()
        MovementLog.objects.create(
            workout_movement=wm,
            sets=[{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}])
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
        self.client.get(self.end_url)  # end existing workout

        self.movement3 = Movement.objects.create(name="Pullup", author=self.user)
        self.current_workout = Workout.objects.create(user=self.user)
        wm2 = WorkoutMovement.objects.create(workout=self.current_workout, movement=self.movement2, order=0)
        wm3 = WorkoutMovement.objects.create(workout=self.current_workout, movement=self.movement3, order=1)

        # Old workout logs (previous session)
        old_wm1 = self.workout.workout_movements.filter(movement=self.movement1).first()
        old_wm2 = self.workout.workout_movements.filter(movement=self.movement2).first()
        MovementLog.objects.create(
            workout_movement=old_wm1,
            sets=[{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now() - datetime.timedelta(seconds=15))
        MovementLog.objects.create(
            workout_movement=old_wm2,
            sets=[{'reps': 8, 'load': 120.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now() - datetime.timedelta(seconds=10))

        # Current workout logs
        MovementLog.objects.create(
            workout_movement=wm2,
            sets=[{'reps': 10, 'load': 130.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now() - datetime.timedelta(seconds=5))
        MovementLog.objects.create(
            workout_movement=wm3,
            sets=[{'reps': 5, 'load': 200.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now())

        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['movements_details']), 2)
        self.assertTrue(any(d['name'] == "Pullup" for d in response.data['movements_details']))
        self.assertTrue(any(d['name'] == "Bench Press" for d in response.data['movements_details']))
        self.assertTrue(all(d['latest_log']['for_current_workout'] == True for d in response.data['movements_details']))

    def test_current_workout_half_complete(self):
        self.client.get(self.end_url)  # end existing workout

        self.movement3 = Movement.objects.create(name="Pullup", author=self.user)
        self.current_workout = Workout.objects.create(user=self.user)
        wm2_old = self.workout.workout_movements.filter(movement=self.movement2).first()
        wm3 = WorkoutMovement.objects.create(workout=self.current_workout, movement=self.movement2, order=0)
        wm4 = WorkoutMovement.objects.create(workout=self.current_workout, movement=self.movement3, order=1)

        old_wm1 = self.workout.workout_movements.filter(movement=self.movement1).first()
        MovementLog.objects.create(
            workout_movement=old_wm1,
            sets=[{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now() - datetime.timedelta(seconds=10))
        MovementLog.objects.create(
            workout_movement=wm2_old,
            sets=[{'reps': 8, 'load': 130.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now() - datetime.timedelta(seconds=5))
        MovementLog.objects.create(
            workout_movement=wm4,
            sets=[{'reps': 5, 'load': 200.0, 'type': 'working', 'rest_time': 120}],
            timestamp=timezone.now())

        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['movements_details']), 2)
        self.assertTrue(any(d['name'] == "Pullup" for d in response.data['movements_details']))
        self.assertTrue(any(d['name'] == "Bench Press" for d in response.data['movements_details']))
        self.assertTrue(any(d['latest_log']['for_current_workout'] == False for d in response.data['movements_details']))

    def test_current_workout_nonexistent_fails(self):
        self.client.get(self.end_url)  # end existing workout
        response = self.client.get(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WorkoutMovementTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="test@example.com", password="password")
        cls.movement1 = Movement.objects.create(name="Squat", author=cls.user)
        cls.movement2 = Movement.objects.create(name="Bench Press", author=cls.user)
        cls.template = MovementLogTemplate.objects.create(
            author=cls.user, name="5x5", movement=cls.movement1,
            sets=[{'reps': '5', 'type': 'working', 'rest_time': 180}])
        cls.workout = Workout.objects.create(user=cls.user)
        cls.wm = WorkoutMovement.objects.create(workout=cls.workout, movement=cls.movement1, order=0)
        cls.list_url = reverse('workout-movement-list')
        cls.detail_url = reverse('workout-movement-detail', kwargs={'id': cls.wm.id})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    def test_authentication_requirements(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(self.detail_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_workout_movements(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['movement'], self.movement1.id)

    def test_list_workout_movements_filter_by_workout(self):
        url = f"{self.list_url}?workout={self.workout.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_list_workout_movements_alt_user_sees_none(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

    def test_create_workout_movement(self):
        data = {'workout': self.workout.id, 'movement': self.movement2.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['order'], 1)  # auto-assigned

    def test_create_workout_movement_with_template(self):
        data = {'workout': self.workout.id, 'movement': self.movement2.id, 'template': self.template.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template'], self.template.id)

    def test_create_workout_movement_not_owning_workout_fails(self):
        alt_user = User.objects.create_user(email="alt2@example.com", password="altpassword")
        alt_workout = Workout.objects.create(user=alt_user)
        data = {'workout': alt_workout.id, 'movement': self.movement1.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_workout_movement_not_owning_movement_fails(self):
        alt_user = User.objects.create_user(email="alt3@example.com", password="altpassword")
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        data = {'workout': self.workout.id, 'movement': alt_movement.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_workout_movement(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['movement'], self.movement1.id)
        self.assertEqual(response.data['order'], 0)

    def test_retrieve_alt_user_fails(self):
        alt_user = User.objects.create_user(email="alt4@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_template(self):
        response = self.client.patch(self.detail_url, {'template': self.template.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['template'], self.template.id)

    def test_delete_workout_movement(self):
        wm = WorkoutMovement.objects.create(workout=self.workout, movement=self.movement2, order=1)
        url = reverse('workout-movement-detail', kwargs={'id': wm.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_workout_movement_with_log_fails(self):
        MovementLog.objects.create(
            workout_movement=self.wm,
            sets=[{'reps': 5, 'load': 100.0, 'type': 'working', 'rest_time': 120}])
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MovementLogTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        mock_now = datetime.datetime(2020, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
        with mock.patch('django.utils.timezone.now', return_value=mock_now):
            MovementLog._meta.get_field('timestamp').default = timezone.now

            cls.user = User.objects.create_user(email="test@example.com", password="password")

            cls.movement1 = Movement.objects.create(name="Squat", author=cls.user)
            cls.movement2 = Movement.objects.create(name="Bench Press", author=cls.user)

            cls.workout1 = Workout.objects.create(user=cls.user)
            cls.workout2 = Workout.objects.create(user=cls.user)

            cls.wm1 = WorkoutMovement.objects.create(workout=cls.workout1, movement=cls.movement1, order=0)
            cls.wm2a = WorkoutMovement.objects.create(workout=cls.workout2, movement=cls.movement2, order=0)

            cls.movement1_log1 = MovementLog.objects.create(
                workout_movement=cls.wm1,
                sets=[{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}])
            cls.movement2_log1 = MovementLog.objects.create(
                workout_movement=cls.wm2a,
                sets=[{'reps': 8, 'load': 130.0, 'type': 'working', 'rest_time': 120}])

            # Two more workouts for movement2 to test filtering
            cls.workout3 = Workout.objects.create(user=cls.user)
            cls.workout4 = Workout.objects.create(user=cls.user)
            cls.wm2b = WorkoutMovement.objects.create(workout=cls.workout3, movement=cls.movement2, order=0)
            cls.wm2c = WorkoutMovement.objects.create(workout=cls.workout4, movement=cls.movement2, order=0)
            cls.movement2_log2 = MovementLog.objects.create(
                workout_movement=cls.wm2b,
                sets=[{'reps': 10, 'load': 130.0, 'type': 'working', 'rest_time': 120}])
            cls.movement2_log3 = MovementLog.objects.create(
                workout_movement=cls.wm2c,
                sets=[{'reps': 9, 'load': 135.0, 'type': 'working', 'rest_time': 120}])

        cls.list_url = reverse('movement-log-list')
        cls.list_url_with_movement = f"{reverse('movement-log-list')}?{urlencode({'movement': cls.movement1.id})}"
        cls.list_url_with_workout = f"{reverse('movement-log-list')}?{urlencode({'workout': cls.workout1.id})}"
        cls.detail_url = reverse('movement-log-detail', kwargs={'id': cls.movement1_log1.id})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    def test_authentication_requirements(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movement_logs(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        response_movement_ids = [log['movement_detail']['id'] for log in response.data['results']]
        expected_movement_ids = [self.movement1.id, self.movement2.id, self.movement2.id, self.movement2.id]
        self.assertCountEqual(response_movement_ids, expected_movement_ids)

    def test_list_movement_logs_alt_user(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

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
        self.assertEqual(response.data['results'][0]['workout_movement'], self.wm1.id)

    @mock.patch('django.utils.timezone.now',
            mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_create_movement_log(self):
        # Create a new workout movement without a log to use for creation
        new_workout = Workout.objects.create(user=self.user)
        new_wm = WorkoutMovement.objects.create(workout=new_workout, movement=self.movement2, order=0)

        sets = [{'reps': 3, 'load': 123.0, 'type': 'working', 'rest_time': 120}]
        movement_log_data = {'workout_movement': new_wm.id, 'sets': sets}
        response = self.client.post(self.list_url, movement_log_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 5)
        self.assertTrue(any(result['sets'] == sets for result in response.data['results']))
        self.assertTrue(
            any(parser.isoparse(result['timestamp']) ==
                    datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)
                for result in response.data['results'])
        )

    def test_create_movement_log_missing_workout_movement_field_fails(self):
        sets = [{'reps': 3, 'load': 123.0, 'type': 'working', 'rest_time': 120}]
        response = self.client.post(self.list_url, {'sets': sets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_invalid_workout_movement_fails(self):
        sets = [{'reps': 3, 'load': 123.0, 'type': 'working', 'rest_time': 120}]
        response = self.client.post(self.list_url, {'workout_movement': 999, 'sets': sets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_not_owning_workout_movement_fails(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        alt_workout = Workout.objects.create(user=alt_user)
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        alt_wm = WorkoutMovement.objects.create(workout=alt_workout, movement=alt_movement, order=0)

        sets = [{'reps': 3, 'load': 123.0, 'type': 'working', 'rest_time': 120}]
        response = self.client.post(self.list_url, {'workout_movement': alt_wm.id, 'sets': sets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_empty_sets_fails(self):
        new_workout = Workout.objects.create(user=self.user)
        new_wm = WorkoutMovement.objects.create(workout=new_workout, movement=self.movement1, order=0)
        response = self.client.post(self.list_url, {'workout_movement': new_wm.id, 'sets': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_invalid_set_type_fails(self):
        new_workout = Workout.objects.create(user=self.user)
        new_wm = WorkoutMovement.objects.create(workout=new_workout, movement=self.movement1, order=0)
        sets = [{'reps': 3, 'load': 123.0, 'type': 'invalid_type', 'rest_time': 120}]
        response = self.client.post(self.list_url, {'workout_movement': new_wm.id, 'sets': sets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movement_log_optional_set_fields(self):
        new_workout = Workout.objects.create(user=self.user)
        new_wm = WorkoutMovement.objects.create(workout=new_workout, movement=self.movement1, order=0)
        sets = [{'reps': 5, 'type': 'working'}]
        response = self.client.post(self.list_url, {'workout_movement': new_wm.id, 'sets': sets}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_movement_log(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sets'], [{'reps': 5, 'load': 25.0, 'type': 'working', 'rest_time': 120}])

    def test_retrieve_nonexistent_movement_log_fails(self):
        url = reverse('movement-log-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_movement_log_alt_user(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('django.utils.timezone.now',
            mock.Mock(return_value=datetime.datetime(2021, 3, 12, 0, 0, 0, tzinfo=pytz.utc)))
    def test_update_movement_log(self):
        sets = [{'reps': 1, 'load': 2.0, 'type': 'working', 'rest_time': None}]
        data = {'workout_movement': self.wm1.id, 'sets': sets}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.data['movement_detail']['id'], self.movement1.id)
        self.assertEqual(response.data['workout_movement'], self.wm1.id)
        self.assertEqual(response.data['sets'], sets)
        self.assertEqual(  # assert timestamp is unchanged
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

    def test_update_movement_log_not_owning_workout_movement_fails(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        alt_workout = Workout.objects.create(user=alt_user)
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        alt_wm = WorkoutMovement.objects.create(workout=alt_workout, movement=alt_movement, order=0)

        sets = [{'reps': 1, 'load': 2.0, 'type': 'working', 'rest_time': None}]
        data = {'workout_movement': alt_wm.id, 'sets': sets}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movement_log_empty_sets_fails(self):
        response = self.client.patch(self.detail_url, {'sets': []}, format='json')
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


class MovementLogTemplateTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="test@example.com", password="password")
        cls.movement = Movement.objects.create(name="Squat", author=cls.user)
        cls.template = MovementLogTemplate.objects.create(
            author=cls.user,
            name="Squat 5x5",
            movement=cls.movement,
            sets=[{'reps': '5', 'type': 'working', 'rest_time': 180}],
        )
        cls.list_url = reverse('movement-log-template-list')
        cls.list_url_with_movement = f"{cls.list_url}?movement={cls.movement.id}"
        cls.detail_url = reverse('movement-log-template-detail', kwargs={'id': cls.template.id})

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    def test_authentication_requirements(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self.detail_url, data={}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_templates(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Squat 5x5')

    def test_list_templates_alt_user_sees_none(self):
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_list_templates_filter_by_movement(self):
        other_movement = Movement.objects.create(name="Bench Press", author=self.user)
        MovementLogTemplate.objects.create(
            author=self.user, name="Generic", sets=[{'reps': '8-10', 'type': 'working'}])
        MovementLogTemplate.objects.create(
            author=self.user, name="Bench Hypertrophy", movement=other_movement,
            sets=[{'reps': '8-10', 'type': 'working'}])

        response = self.client.get(self.list_url_with_movement)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Squat 5x5')

    def test_create_template_with_movement(self):
        data = {
            'name': 'Squat 3x8',
            'movement': self.movement.id,
            'sets': [{'reps': '8', 'type': 'working', 'rest_time': 120}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.user.id)
        self.assertEqual(response.data['movement'], self.movement.id)

    def test_create_generic_template_without_movement(self):
        data = {
            'name': 'Generic Hypertrophy',
            'sets': [{'reps': '8-12', 'type': 'working', 'rest_time': 90}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['movement'])

    def test_create_template_with_movement_not_owned_fails(self):
        alt_user = User.objects.create_user(email="alt2@example.com", password="altpassword")
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        data = {
            'name': 'Deadlift 5x5',
            'movement': alt_movement.id,
            'sets': [{'reps': '5', 'type': 'working'}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_empty_sets_fails(self):
        data = {'name': 'Empty', 'sets': []}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_template(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Squat 5x5')
        self.assertEqual(response.data['sets'], [{'reps': '5', 'type': 'working', 'rest_time': 180}])

    def test_retrieve_template_alt_user_fails(self):
        alt_user = User.objects.create_user(email="alt3@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_template_fails(self):
        url = reverse('movement-log-template-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_template(self):
        data = {
            'name': 'Squat 5x5 Updated',
            'movement': self.movement.id,
            'sets': [{'reps': '5', 'type': 'working', 'rest_time': 180}],
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Squat 5x5 Updated')

    def test_partial_update_template(self):
        response = self.client.patch(self.detail_url, {'name': 'Squat 5x5 Patched'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Squat 5x5 Patched')

    def test_delete_template(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

    def test_delete_nonexistent_template_fails(self):
        url = reverse('movement-log-template-detail', kwargs={'id': 123})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_template_alt_user_fails(self):
        alt_user = User.objects.create_user(email="alt4@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Reps field validation

    def test_reps_single_number_valid(self):
        data = {'name': 'T', 'sets': [{'reps': '5', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reps_range_valid(self):
        data = {'name': 'T', 'sets': [{'reps': '8-10', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reps_invalid_string_fails(self):
        data = {'name': 'T', 'sets': [{'reps': 'abc', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reps_range_min_equals_max_fails(self):
        data = {'name': 'T', 'sets': [{'reps': '8-8', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reps_range_min_greater_than_max_fails(self):
        data = {'name': 'T', 'sets': [{'reps': '10-8', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reps_zero_fails(self):
        data = {'name': 'T', 'sets': [{'reps': '0', 'type': 'working'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_set_type_fails(self):
        data = {'name': 'T', 'sets': [{'reps': '5', 'type': 'invalid'}]}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WorkoutTemplateTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="test@example.com", password="password")
        cls.movement1 = Movement.objects.create(name="Squat", author=cls.user)
        cls.movement2 = Movement.objects.create(name="Bench Press", author=cls.user)
        cls.mlt1 = MovementLogTemplate.objects.create(
            author=cls.user, name="Squat 5x5", movement=cls.movement1,
            sets=[{'reps': '5', 'type': 'working', 'rest_time': 300}])
        cls.mlt2 = MovementLogTemplate.objects.create(
            author=cls.user, name="Bench 4x8", movement=cls.movement2,
            sets=[{'reps': '8-10', 'type': 'working', 'rest_time': 180}])

        # A finished workout with movements and templates assigned
        cls.past_workout = Workout.objects.create(user=cls.user)
        cls.past_wm1 = WorkoutMovement.objects.create(
            workout=cls.past_workout, movement=cls.movement1, template=cls.mlt1, order=0)
        cls.past_wm2 = WorkoutMovement.objects.create(
            workout=cls.past_workout, movement=cls.movement2, template=cls.mlt2, order=1)
        MovementLog.objects.create(
            workout_movement=cls.past_wm1,
            sets=[{'reps': 5, 'load': 100.0, 'type': 'working', 'rest_time': 300}])
        cls.past_workout.end_timestamp = timezone.now()
        cls.past_workout.save()

        cls.list_url = reverse('workout-template-list')
        cls.workout_list_url = reverse('workout-list')

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.client.force_authenticate(user=None)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def test_authentication_requirements(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Auth Test")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        detail_url = reverse('workout-template-detail', kwargs={'id': wt.id})
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url, {}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(detail_url, {}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ──────────────────────────────────────────────────────────────────

    def test_list_templates_empty(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_list_templates(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="My Template")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'My Template')

    def test_list_templates_alt_user_sees_none(self):
        WorkoutTemplate.objects.create(author=self.user, name="Private Template")
        alt_user = User.objects.create_user(email="alt@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data['count'], 0)

    # ── Create from scratch ───────────────────────────────────────────────────

    def test_create_template_from_scratch(self):
        data = {
            'name': 'Push Day',
            'movements': [
                {'movement': self.movement1.id, 'movement_log_template': None},
                {'movement': self.movement2.id, 'movement_log_template': None},
            ],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Push Day')
        self.assertEqual(len(response.data['movements_details']), 2)
        self.assertEqual(response.data['movements_details'][0]['movement'], self.movement1.id)
        self.assertEqual(response.data['movements_details'][1]['movement'], self.movement2.id)
        self.assertIsNone(response.data['movements_details'][0]['movement_log_template'])

    def test_create_template_from_scratch_with_movement_log_templates(self):
        data = {
            'name': 'Push Day With Templates',
            'movements': [
                {'movement': self.movement1.id, 'movement_log_template': self.mlt1.id},
                {'movement': self.movement2.id, 'movement_log_template': self.mlt2.id},
            ],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['movements_details'][0]['movement_log_template'], self.mlt1.id)
        self.assertEqual(response.data['movements_details'][1]['movement_log_template'], self.mlt2.id)

    def test_create_template_order_preserved(self):
        data = {
            'name': 'Order Test',
            'movements': [
                {'movement': self.movement2.id, 'movement_log_template': None},
                {'movement': self.movement1.id, 'movement_log_template': None},
            ],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        details = response.data['movements_details']
        self.assertEqual(details[0]['movement'], self.movement2.id)
        self.assertEqual(details[1]['movement'], self.movement1.id)

    # ── Create from source_workout ────────────────────────────────────────────

    def test_create_template_from_source_workout(self):
        data = {'name': 'From Workout', 'source_workout': self.past_workout.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'From Workout')
        details = response.data['movements_details']
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0]['movement'], self.movement1.id)
        self.assertEqual(details[1]['movement'], self.movement2.id)

    def test_create_template_from_source_workout_copies_movement_log_templates(self):
        data = {'name': 'Copies Templates', 'source_workout': self.past_workout.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        details = response.data['movements_details']
        self.assertEqual(details[0]['movement_log_template'], self.mlt1.id)
        self.assertEqual(details[1]['movement_log_template'], self.mlt2.id)

    def test_create_template_from_source_workout_preserves_order(self):
        data = {'name': 'Order From Workout', 'source_workout': self.past_workout.id}
        response = self.client.post(self.list_url, data, format='json')
        details = response.data['movements_details']
        self.assertEqual(details[0]['order'], 0)
        self.assertEqual(details[1]['order'], 1)

    def test_create_template_source_workout_not_owned_fails(self):
        alt_user = User.objects.create_user(email="alt2@example.com", password="altpassword")
        alt_workout = Workout.objects.create(user=alt_user)
        data = {'name': 'Bad Source', 'source_workout': alt_workout.id}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Validation ────────────────────────────────────────────────────────────

    def test_create_template_name_duplicate_fails(self):
        WorkoutTemplate.objects.create(author=self.user, name="Duplicate")
        data = {
            'name': 'Duplicate',
            'movements': [{'movement': self.movement1.id, 'movement_log_template': None}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_name_duplicate_different_user_succeeds(self):
        WorkoutTemplate.objects.create(author=self.user, name="Shared Name")
        alt_user = User.objects.create_user(email="alt3@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        data = {
            'name': 'Shared Name',
            'movements': [{'movement': alt_movement.id, 'movement_log_template': None}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_template_both_source_workout_and_movements_fails(self):
        data = {
            'name': 'Both',
            'source_workout': self.past_workout.id,
            'movements': [{'movement': self.movement1.id, 'movement_log_template': None}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_neither_source_workout_nor_movements_fails(self):
        response = self.client.post(self.list_url, {'name': 'Empty'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_movement_not_owned_fails(self):
        alt_user = User.objects.create_user(email="alt5@example.com", password="altpassword")
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)
        data = {
            'name': 'Bad Movement',
            'movements': [{'movement': alt_movement.id, 'movement_log_template': None}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_template_movement_log_template_not_owned_fails(self):
        alt_user = User.objects.create_user(email="alt6@example.com", password="altpassword")
        alt_mlt = MovementLogTemplate.objects.create(
            author=alt_user, name="Alt Template",
            sets=[{'reps': '5', 'type': 'working'}])
        data = {
            'name': 'Bad MLT',
            'movements': [{'movement': self.movement1.id, 'movement_log_template': alt_mlt.id}],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def test_retrieve_template(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Retrieve Me")
        WorkoutTemplateMovement.objects.create(
            template=wt, movement=self.movement1, movement_log_template=self.mlt1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Retrieve Me')
        self.assertEqual(len(response.data['movements_details']), 1)
        self.assertEqual(response.data['movements_details'][0]['movement_log_template'], self.mlt1.id)
        self.assertIsNotNone(response.data['movements_details'][0]['movement_log_template_detail'])

    def test_retrieve_template_alt_user_fails(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Private")
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        alt_user = User.objects.create_user(email="alt7@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_template_fails(self):
        url = reverse('workout-template-detail', kwargs={'id': 123})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Update ────────────────────────────────────────────────────────────────

    def test_update_template_name(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Old Name")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        response = self.client.patch(url, {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New Name')

    def test_update_template_movements(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Update Movements")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        data = {'movements': [
            {'movement': self.movement2.id, 'movement_log_template': self.mlt2.id},
        ]}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['movements_details']), 1)
        self.assertEqual(response.data['movements_details'][0]['movement'], self.movement2.id)
        self.assertEqual(response.data['movements_details'][0]['movement_log_template'], self.mlt2.id)

    def test_update_template_name_duplicate_fails(self):
        WorkoutTemplate.objects.create(author=self.user, name="Existing")
        wt = WorkoutTemplate.objects.create(author=self.user, name="To Rename")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        response = self.client.patch(url, {'name': 'Existing'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_template_same_name_succeeds(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Same Name")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        response = self.client.patch(url, {'name': 'Same Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_template(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Delete Me")
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkoutTemplate.objects.filter(id=wt.id).exists())

    def test_delete_template_cascades_movements(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Cascade Test")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        self.client.delete(url)
        self.assertEqual(WorkoutTemplateMovement.objects.filter(template=wt).count(), 0)

    def test_delete_nonexistent_template_fails(self):
        url = reverse('workout-template-detail', kwargs={'id': 123})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_template_alt_user_fails(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Protected")
        url = reverse('workout-template-detail', kwargs={'id': wt.id})
        alt_user = User.objects.create_user(email="alt8@example.com", password="altpassword")
        self.client.force_authenticate(user=alt_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Start workout from template ───────────────────────────────────────────

    def test_start_workout_from_template(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Workout Source")
        WorkoutTemplateMovement.objects.create(
            template=wt, movement=self.movement1, movement_log_template=self.mlt1, order=0)
        WorkoutTemplateMovement.objects.create(
            template=wt, movement=self.movement2, movement_log_template=None, order=1)

        response = self.client.post(self.workout_list_url, {'template': wt.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        details = response.data['movements_details']
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0]['id'], self.movement1.id)
        self.assertEqual(details[1]['id'], self.movement2.id)

    def test_start_workout_from_template_copies_movement_log_templates(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="With MLTs")
        WorkoutTemplateMovement.objects.create(
            template=wt, movement=self.movement1, movement_log_template=self.mlt1, order=0)

        response = self.client.post(self.workout_list_url, {'template': wt.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify via current workout endpoint that template was assigned
        current = self.client.get(reverse('workout-current')).json()
        self.assertEqual(current['movements_details'][0]['template']['id'], self.mlt1.id)

    def test_start_workout_from_template_movement_not_owned_fails(self):
        alt_user = User.objects.create_user(email="alt9@example.com", password="altpassword")
        alt_movement = Movement.objects.create(name="Deadlift", author=alt_user)

        # Bypass serializer validation to create a template with an unowned movement
        wt = WorkoutTemplate.objects.create(author=self.user, name="Bad Template")
        WorkoutTemplateMovement.objects.create(template=wt, movement=alt_movement, order=0)

        response = self.client.post(self.workout_list_url, {'template': wt.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_workout_with_template_and_movements_fails(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Conflict")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=0)
        data = {'template': wt.id, 'movements': [self.movement1.id]}
        response = self.client.post(self.workout_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_workout_from_template_preserves_order(self):
        wt = WorkoutTemplate.objects.create(author=self.user, name="Order Check")
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement2, order=0)
        WorkoutTemplateMovement.objects.create(template=wt, movement=self.movement1, order=1)

        response = self.client.post(self.workout_list_url, {'template': wt.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        details = response.data['movements_details']
        self.assertEqual(details[0]['id'], self.movement2.id)
        self.assertEqual(details[1]['id'], self.movement1.id)
