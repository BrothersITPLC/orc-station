from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def get_token(cls, user):
        token = super().get_token(user)
        return token

    def validate(self, attrs):

        data = super().validate(attrs)

        try:

            data.update({"username": self.user.username})
            data.update({"email": self.user.email})
            data.update({"first_name": self.user.first_name})
            data.update({"last_name": self.user.last_name})
            data.update({"id": self.user.id})
            if self.user.current_station:
                data.update({"current_station": (self.user.current_station)})
            else:
                data.update({"current_station": None})

            if self.user.role:

                data.update({"role": self.user.role.name})

            else:
                data.update({"role": None})

            return data
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
