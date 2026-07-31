from django import forms
from .models import StockEntry, ConsumptionUpload, Material


class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ["date", "material", "opening", "received", "consumed", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.warehouse = warehouse
        self.fields["material"].queryset = Material.objects.filter(is_active=True)


class ConsumptionUploadForm(forms.ModelForm):
    class Meta:
        model = ConsumptionUpload
        fields = ["file"]
