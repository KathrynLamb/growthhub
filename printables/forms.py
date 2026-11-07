# printables/forms.py
import re

from django import forms

from moments.models import Moment

from .models import PrintableRequest

NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' \-]{1,30}$")


class PrintableRequestForm(forms.ModelForm):
    moment = forms.ModelChoiceField(
        queryset=Moment.objects.none(),
        required=False,
        empty_label="Just a fun adventure",
        label="What's the story about?",
    )
    # Honeypot: real people never see or fill this in.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = PrintableRequest
        fields = ["child_name", "child_age", "interests", "moment", "email", "confirmed_parent", "marketing_opt_in"]
        labels = {
            "child_name": "Child's first name",
            "child_age": "Age",
            "interests": "Things they love (optional)",
            "email": "Your email",
            "confirmed_parent": "I'm the child's parent or carer, and I'm over 18",
            "marketing_opt_in": "Send me occasional story ideas from FlipWhizz (you can unsubscribe any time)",
        }
        widgets = {
            "child_age": forms.Select(choices=[(i, str(i)) for i in range(1, 9)]),
            "interests": forms.TextInput(attrs={"maxlength": 120, "placeholder": "dinosaurs, the seaside, our dog Pepper"}),
            "child_name": forms.TextInput(attrs={"maxlength": 30, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["moment"].queryset = Moment.objects.published()
        self.fields["confirmed_parent"].required = True
        self.fields["child_age"].initial = self.initial.get("child_age", 4)

    def clean_child_name(self):
        name = " ".join(self.cleaned_data["child_name"].split())
        if not NAME_PATTERN.match(name):
            raise forms.ValidationError("Please use letters only, up to 30 characters.")
        return name

    def clean_child_age(self):
        age = self.cleaned_data["child_age"]
        if not 1 <= age <= 8:
            raise forms.ValidationError("These stories are for ages 1 to 8.")
        return age

    def clean_interests(self):
        # Collapse whitespace and strip characters that could be used to smuggle
        # instructions to the story model (braces, angle brackets, backticks).
        text = " ".join(self.cleaned_data.get("interests", "").split())
        return re.sub(r"[{}<>`\\]", "", text)[:120]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam check failed.")
        return ""
