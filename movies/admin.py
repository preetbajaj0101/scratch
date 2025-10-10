# movies/admin.py

from django.contrib import admin
from django import forms
from .models import Movie, Theater, Seat, Booking, Genre, Language

# Custom form to validate the number of genres
class MovieAdminForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = '__all__'

    def clean_genres(self):
        genres = self.cleaned_data.get('genres')
        if not genres:
            raise forms.ValidationError('You must select at least one genre.')
        if len(genres) > 8:
            raise forms.ValidationError('You cannot select more than 8 genres.')
        return genres

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    form = MovieAdminForm
    list_display = ['name', 'language', 'rating']
    list_filter = ['language', 'genres']
    search_fields = ['name', 'cast']
    filter_horizontal = ('genres',) # Use a more user-friendly widget for many-to-many fields

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time']

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'seat', 'movie', 'theater', 'booked_at']

# Register the new models
admin.site.register(Genre)
admin.site.register(Language)