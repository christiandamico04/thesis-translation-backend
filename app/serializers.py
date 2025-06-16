from rest_framework import serializers
from .models import File, Translation

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'
        read_only_fields = ('user',)                # Dice al serializer: "Il campo 'user' non verrà fornito dal client, 
                                                    # ma sarà aggiunto dal backend. Consideralo in sola lettura durante la validazione.
class TranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = '__all__'
