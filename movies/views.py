# movies/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from utils.email_utils import send_booking_confirmation_email
from .models import Movie, Theater, Seat, Booking, Genre, Language
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

def movie_list(request):
    # Start with all movies
    movies = Movie.objects.all()

    # Get all available genres and languages for the filter dropdowns
    genres = Genre.objects.all()
    languages = Language.objects.all()

    # Get filter parameters from the URL
    search_query = request.GET.get('search')
    selected_genre_id = request.GET.get('genre')
    selected_language_id = request.GET.get('language')

    # Apply filters to the queryset
    if search_query:
        movies = movies.filter(name__icontains=search_query)

    if selected_genre_id:
        movies = movies.filter(genres__id=selected_genre_id)

    if selected_language_id:
        movies = movies.filter(language__id=selected_language_id)

    context = {
        'movies': movies,
        'genres': genres,
        'languages': languages,
        # Pass selected values back to template to keep them selected
        'selected_genre_id': selected_genre_id,
        'selected_language_id': selected_language_id,
    }
    return render(request, 'movies/movie_list.html', context)

# THIS IS THE MISSING FUNCTION THAT NEEDS TO BE ADDED BACK
def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie': movie, 'theaters': theaters})

@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theaters = get_object_or_404(Theater, id=theater_id)
    # Get seats and arrange them in alphanumeric order (row letters, then column numbers)
    seats_qs = Seat.objects.filter(theater=theaters)
    # Sort in Python to keep it DB-agnostic and to support labels like A1, B10, etc.
    def seat_key(seat):
        sn = seat.seat_number or ''
        letters = ''.join([ch for ch in sn if ch.isalpha()])
        nums = ''.join([ch for ch in sn if ch.isdigit()])
        try:
            num_val = int(nums) if nums else 0
        except ValueError:
            num_val = 0
        return (letters, num_val)

    try:
        seats_sorted = sorted(seats_qs, key=seat_key)
        # Group by row letters
        from itertools import groupby
        seats_rows = []
        for row_letter, group in groupby(seats_sorted, key=lambda s: ''.join([ch for ch in (s.seat_number or '') if ch.isalpha()])):
            seats_rows.append((row_letter, list(group)))
        # Reverse rows so Z appears first and A last (presentation order)
        seats_rows.reverse()
    except Exception as e:
        # Defensive fallback: if labels are malformed or unexpected, don't crash the page.
        # Log to console (server terminal) and present a flat list to the template.
        import sys
        print('Error while sorting/grouping seats:', e, file=sys.stderr)
        seats_sorted = list(seats_qs)
        seats_rows = [('', seats_sorted)]
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        if not selected_Seats:
            return render(request, "movies/seat_selection.html", {'theaters': theaters, "seats": seats_qs, 'seats_rows': seats_rows, 'error': "No seat selected"})
        for seat_id in selected_Seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theaters)
            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue
            try:
                Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theaters.movie,
                    theater=theaters
                )
                seat.is_booked = True
                seat.save()
            except IntegrityError:
                error_seats.append(seat.seat_number)
        if error_seats:
            error_message = f"The following seats are already booked:{','.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seats": seats_qs, 'seats_rows': seats_rows, 'error': error_message})
        # All selected seats successfully booked. Send a confirmation email.
        # Collect only the seat labels that were just booked in this request (selected_Seats)
        created_seats = []
        for seat_id in selected_Seats:
            try:
                s = Seat.objects.get(id=seat_id)
                created_seats.append(s.seat_number)
            except Seat.DoesNotExist:
                pass
        # Build email context
        email_context = {
            'user': request.user,
            'movie': theaters.movie,
            'theater': theaters,
            'seats': created_seats,
        }

        # Send booking confirmation email via utility
        try:
            send_booking_confirmation_email(request.user, theaters.movie, theaters, created_seats)
        except Exception as e:
            import sys
            print('Error sending booking confirmation email:', e, file=sys.stderr)

        return redirect('profile')
    return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seats": seats_qs, 'seats_rows': seats_rows})
# End of file
