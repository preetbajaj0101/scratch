# movies/views.py

from django.shortcuts import render, redirect, get_object_or_404
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
    seats = Seat.objects.filter(theater=theaters)
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        if not selected_Seats:
            return render(request, "movies/seat_selection.html", {'theaters': theaters, "seats": seats, 'error': "No seat selected"})
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
            return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seats": seats, 'error': error_message})
        return redirect('profile')
    return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seats": seats})