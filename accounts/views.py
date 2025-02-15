from .forms import SignUpForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib import messages
from django.shortcuts import render, redirect


class SignUpView(generic.CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy("login")
    initial = None  # принимает {'key': 'value'}
    template_name = "registration/signup.html"

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Вы успешно зарегистрировались {username}')

            return redirect(to='/')

        return render(request, self.template_name, {'form': form})

    # def form_valid(self, form):
    #     response = super().form_valid(form)
    #     messages.success(self.request, "Вы успешно зарегистрировались")
    #     return response
