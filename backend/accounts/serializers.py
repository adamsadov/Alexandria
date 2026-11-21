from rest_framework import serializers
from .models import User, UserProfile

# User profile
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_pic =serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ('bio', 'zip_code', 'social_links', 'username', 'profile_pic')

    def get_profile_pic(self, obj):
        # Get the profile picture from the user model
        return obj.user.profile_pic if obj.user else None
        
    def get_username(self, obj):
        # Get the username from the user model
        return obj.user.username if obj.user else None

class PublicUserSerializer(serializers.ModelSerializer):
    profile_pic_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_pic', 'profile_pic_url']
    
    def get_profile_pic_url(self, obj):
        """
        Return the full URL for the profile picture if it exists
        """
        if not obj.profile_pic:
            return None
            
        # If it's already a full URL, return as-is
        if obj.profile_pic.startswith(('http://', 'https://')):
            return obj.profile_pic
        
        # Get the request from context
        request = self.context.get('request')
        
        # If request is available, use build_absolute_uri
        if request:
            return request.build_absolute_uri(obj.profile_pic)
        
        # Fallback to hardcoded URL
        base_url = 'http://localhost:8000'
        
        # Ensure the path starts with /media/
        profile_pic = obj.profile_pic if obj.profile_pic.startswith('/media/') else f'/media/{obj.profile_pic}'
        
        return f"{base_url}{profile_pic}"
