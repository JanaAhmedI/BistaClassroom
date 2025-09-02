from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from ..decorators import student_required
from ..forms import StudentInterestsForm, StudentSignUpForm, TakeQuizForm
from ..models import Quiz, Student, TakenQuiz, User, Answer, StudentAnswer

from datetime import timedelta
from django.utils import timezone

class StudentSignUpView(CreateView):
    model = User
    form_class = StudentSignUpForm
    template_name = 'registration/signup_form.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'student'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('students:quiz_list')


@method_decorator([login_required, student_required], name='dispatch')
class StudentInterestsView(UpdateView):
    model = Student
    form_class = StudentInterestsForm
    template_name = 'classroom/students/interests_form.html'
    success_url = reverse_lazy('students:quiz_list')

    def get_object(self):
        return self.request.user.student

    def form_valid(self, form):
        messages.success(self.request, 'Interests updated with success!')
        return super().form_valid(form)


@method_decorator([login_required, student_required], name='dispatch')
class QuizListView(ListView):
    model = Quiz
    ordering = ('name', )
    context_object_name = 'quizzes'
    template_name = 'classroom/students/quiz_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.auto_submit_expired_quizzes()
        return super().dispatch(request, *args, **kwargs)

    def auto_submit_expired_quizzes(self):
        student = self.request.user.student
        now = timezone.now()
        for quiz in Quiz.objects.all():
            session_key = f'quiz_{quiz.pk}_start_time'
            if session_key in self.request.session:
                try:
                    start_time = timezone.datetime.fromisoformat(self.request.session[session_key])
                    end_time = start_time + timedelta(minutes=quiz.duration_minutes)
                    if now >= end_time:
                        if not TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
                            student_answers = StudentAnswer.objects.filter(student=student, answer__question__quiz=quiz)
                            score = round(sum(ans.answer.score for ans in student_answers), 2)
                            TakenQuiz.objects.create(student=student, quiz=quiz, score=score)
                            del self.request.session[session_key]
                except Exception as e:
                    print(f"❌ Error auto submit: {e}")

    def get_queryset(self):
        student = self.request.user.student
        student_interests = student.interests.values_list('pk', flat=True)
        taken_quizzes = student.quizzes.values_list('pk', flat=True)
        queryset = Quiz.objects.filter(subject__in=student_interests) \
            .exclude(pk__in=taken_quizzes) \
            .annotate(questions_count=Count('questions')) \
            .filter(questions_count__gt=0)
        return queryset

@method_decorator([login_required, student_required], name='dispatch')
class TakenQuizListView(ListView):
    model = TakenQuiz
    context_object_name = 'taken_quizzes'
    template_name = 'classroom/students/taken_quiz_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student
        taken_quizzes = self.get_queryset()
        section_ranges = [(1, 30), (31, 65), (66, 110)]

        section_scores = []

        for tq in taken_quizzes:
            quiz = tq.quiz
            scores = []

            for start, end in section_ranges:
                answers = StudentAnswer.objects.filter(
                    student=student,
                    answer__question__quiz=quiz,
                    answer__question__order__gte=start,
                    answer__question__order__lte=end
                )
                score = sum(ans.answer.score for ans in answers)
                scores.append(score)

            section_scores.append({
                'quiz_id': tq.quiz.id,  # ⬅️ Tambahkan ini
                'quiz_name': tq.quiz.name,
                'subject': tq.quiz.subject.get_html_badge(),
                'scores': scores,
                'total_score': tq.score,
            })


        context['section_scores'] = section_scores
        return context

    def get_queryset(self):
        return self.request.user.student.taken_quizzes \
            .select_related('quiz', 'quiz__subject') \
            .order_by('quiz__name')

@login_required
@student_required
def take_quiz_question(request, quiz_pk, question_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk)
    student = request.user.student
    question = get_object_or_404(quiz.questions, pk=question_pk)

    if TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
        return render(request, 'students/taken_quiz.html')

    session_key = f'quiz_{quiz.pk}_start_time'
    if not request.session.get(session_key):
        messages.warning(request, f"Waktu untuk mengerjakan kuis {quiz.name} telah habis.")
        return redirect('students:quiz_list')

    start_time = timezone.datetime.fromisoformat(request.session[session_key])
    end_time = start_time + timedelta(minutes=quiz.duration_minutes)
    remaining_seconds = int((end_time - timezone.now()).total_seconds())

    # ⛔️ Hanya validasi waktu saat GET, bukan saat POST (agar submit timeout tetap diproses)
    if request.method == 'GET' and remaining_seconds <= 0:
        messages.warning(request, f"Waktu untuk mengerjakan kuis {quiz.name} telah habis.")
        return redirect('students:quiz_list')

    total_questions = quiz.questions.count()
    unanswered_questions = student.get_unanswered_questions(quiz)
    total_unanswered_questions = unanswered_questions.count()
    answered_count = total_questions - total_unanswered_questions
    progress = round((answered_count / total_questions) * 100)

    if request.method == 'POST':
        print("📥 POST DATA:", dict(request.POST))
        action = request.POST.get('action')
        selected_answer_id = request.POST.get('answer')

        # Simpan jawaban jika dipilih
        if selected_answer_id:
            try:
                selected_answer = question.answers.get(pk=selected_answer_id)
                StudentAnswer.objects.filter(student=student, answer__question=question).delete()
                StudentAnswer.objects.create(student=student, answer=selected_answer)
                print("✅ Jawaban disimpan:", selected_answer.id)
            except Answer.DoesNotExist:
                print("❌ Jawaban tidak ditemukan")

        # Jika user menyelesaikan kuis (manual atau timeout)
        if action in ['finish', 'timeout_finish'] or student.get_unanswered_questions(quiz).count() == 0:
            print("✅ Proses penyelesaian kuis (manual/otomatis)")
            student_answers = StudentAnswer.objects.filter(student=student, answer__question__quiz=quiz)
            score = round(sum(ans.answer.score for ans in student_answers), 2)
            print("📊 Jawaban:", student_answers.count(), "📈 Skor:", score)

            if not TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
                TakenQuiz.objects.create(student=student, quiz=quiz, score=score)
                print("✅ TakenQuiz dibuat")

            if session_key in request.session:
                del request.session[session_key]
                print("🧹 Session dihapus")

            if score < 50.0:
                messages.warning(request, f'Nilai kamu {score}. Semangat belajar!')
            else:
                messages.success(request, f'Selamat! Kamu menyelesaikan kuis {quiz.name} dengan nilai {score}')
            return redirect('students:quiz_list')

        # Navigasi soal (next, skip, goto_X)
        if action == 'next' or action == 'skip':
            next_question = quiz.questions.filter(pk__gt=question.pk).order_by('pk').first()
            if next_question:
                return redirect('students:take_quiz_question', quiz_pk=quiz.pk, question_pk=next_question.pk)

        elif action and action.startswith("goto_"):
            next_qid = int(action.replace("goto_", ""))
            return redirect('students:take_quiz_question', quiz_pk=quiz.pk, question_pk=next_qid)

        # Otomatis selesai jika semua soal terjawab
        if student.get_unanswered_questions(quiz).count() == 0:
            if not TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
                student_answers = StudentAnswer.objects.filter(student=student, answer__question__quiz=quiz)
                score = round(sum(ans.answer.score for ans in student_answers), 2)
                TakenQuiz.objects.create(student=student, quiz=quiz, score=score)
                if session_key in request.session:
                    del request.session[session_key]
                if score < 50.0:
                    messages.warning(request, f'Nilai kamu {score}. Semangat belajar!')
                else:
                    messages.success(request, f'Selamat! Kamu menyelesaikan kuis {quiz.name} dengan nilai {score}')
            return redirect('students:quiz_list')

    # Ambil jawaban yang sudah dipilih sebelumnya
    try:
        selected_answer_obj = StudentAnswer.objects.filter(student=student, answer__question=question).first()
        selected_answer = selected_answer_obj.answer if selected_answer_obj else None
    except:
        selected_answer = None

    answered_question_ids = list(
        StudentAnswer.objects.filter(student=student, answer__question__quiz=quiz)
        .values_list('answer__question_id', flat=True)
    )

    return render(request, 'classroom/students/take_quiz_form.html', {
        'quiz': quiz,
        'question': question,
        'progress': progress,
        'remaining_seconds': remaining_seconds,
        'selected_answer': selected_answer,
        'answered_question_ids': answered_question_ids,
    })


@login_required
@student_required
def redirect_to_first_question(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    student = request.user.student

    # Cek sudah pernah ikut kuis
    if TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
        return render(request, 'students/taken_quiz.html')

    # Simpan waktu mulai ke sesi (jika belum ada)
    session_key = f'quiz_{quiz.pk}_start_time'
    if not request.session.get(session_key):
        request.session[session_key] = timezone.now().isoformat()

    # Redirect ke soal pertama
    first_question = quiz.questions.first()
    return redirect('students:take_quiz_question', quiz_pk=quiz.pk, question_pk=first_question.pk)

@login_required
@student_required
def view_discussion(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    student = request.user.student

    # Cek apakah siswa sudah menyelesaikan kuis ini
    if not TakenQuiz.objects.filter(student=student, quiz=quiz).exists():
        messages.warning(request, "Anda belum menyelesaikan kuis ini.")
        return redirect('students:quiz_list')

    # Ambil jawaban siswa
    answers = StudentAnswer.objects.filter(
        student=student,
        answer__question__quiz=quiz
    ).select_related('answer', 'answer__question')

    # Susun dictionary {question_id: answer_id}
    student_answer = {ans.answer.question.id: ans.answer.id for ans in answers}

    return render(request, 'classroom/students/view_discussion.html', {
        'quiz': quiz,
        'student_answer': student_answer,
    })


