# movies/admin.py

from django.contrib import admin, messages
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
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

class SeatGenerationForm(forms.Form):
    start_row = forms.CharField(max_length=1, initial='A', help_text='Starting row letter (A-Z)')
    num_rows = forms.IntegerField(min_value=1, max_value=26, initial=5, help_text='Number of rows')
    num_columns = forms.IntegerField(min_value=1, initial=10, help_text='Number of seats per row')


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time']
    actions = ['generate_seats_action']
    change_form_template = 'admin/movies/theater/change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/generate-seats/', self.admin_site.admin_view(self.generate_seats_view), name='movies_theater_generate_seats'),
        ]
        return custom_urls + urls

    def generate_seats_view(self, request, pk):
        # single-theater seat generation view
        theater = Theater.objects.get(pk=pk)
        if request.method == 'POST':
            form = SeatGenerationForm(request.POST)
            if form.is_valid():
                start_row = form.cleaned_data['start_row'].upper()
                num_rows = form.cleaned_data['num_rows']
                num_columns = form.cleaned_data['num_columns']
                created_for_theater = 0
                for r in range(num_rows):
                    row_letter = chr(ord(start_row) + r)
                    if row_letter > 'Z':
                        break
                    for c in range(1, num_columns + 1):
                        seat_label = f"{row_letter}{c}"
                        seat_obj, created = Seat.objects.get_or_create(theater=theater, seat_number=seat_label)
                        if created:
                            created_for_theater += 1

                if created_for_theater:
                    self.message_user(request, f"Created {created_for_theater} seats for {theater}.", level=messages.SUCCESS)
                else:
                    self.message_user(request, f"No new seats created for {theater} (all seats already exist).", level=messages.WARNING)

                return redirect('admin:movies_theater_change', theater.pk)
        else:
            form = SeatGenerationForm()

        context = {
            'form': form,
            'theater': theater,
            'title': f'Generate seats for {theater}',
        }
        return render(request, 'admin/movies/theater/generate_seats_single.html', context)

    def generate_seats_action(self, request, queryset):
        """Admin action to generate seats for selected theaters.

        Shows an intermediate form to collect start_row, num_rows and num_columns.
        Creates alphanumeric seat labels like A1, A2, ... B1, B2, ... in row-major order
        and skips seats that already exist for a theater.
        """
        if 'apply' in request.POST:
            form = SeatGenerationForm(request.POST)
            if form.is_valid():
                start_row = form.cleaned_data['start_row'].upper()
                num_rows = form.cleaned_data['num_rows']
                num_columns = form.cleaned_data['num_columns']

                # If this is the second POST (after the intermediate form), Django's
                # action machinery doesn't pass the queryset again. Rebuild it from
                # the list of selected IDs included as hidden inputs named
                # `_selected_action` in the form.
                if not queryset.exists():
                    selected_ids = request.POST.getlist('_selected_action')
                    queryset = Theater.objects.filter(pk__in=selected_ids)

                total_created = 0
                for theater in queryset:
                    created_for_theater = 0
                    for r in range(num_rows):
                        row_letter = chr(ord(start_row) + r)
                        if row_letter > 'Z':
                            break
                        for c in range(1, num_columns + 1):
                            seat_label = f"{row_letter}{c}"
                            seat_obj, created = Seat.objects.get_or_create(theater=theater, seat_number=seat_label)
                            if created:
                                created_for_theater += 1
                    total_created += created_for_theater
                    if created_for_theater:
                        self.message_user(request, f"Created {created_for_theater} seats for {theater}.", level=messages.SUCCESS)
                    else:
                        self.message_user(request, f"No new seats created for {theater} (all seats already exist).", level=messages.WARNING)

                self.message_user(request, f"Total seats created: {total_created}", level=messages.INFO)
                # Redirect back to the changelist to avoid leaving the action view open
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = SeatGenerationForm()

        context = {
            'form': form,
            'theaters': queryset,
            'title': 'Generate seats for selected theaters',
            'action_name': 'generate_seats_action',
        }
        return render(request, 'admin/movies/theater/generate_seats.html', context)

    generate_seats_action.short_description = 'Generate seats (rows x columns) for selected theaters'

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'seat', 'movie', 'theater', 'booked_at']

# Register the new models
admin.site.register(Genre)
admin.site.register(Language)