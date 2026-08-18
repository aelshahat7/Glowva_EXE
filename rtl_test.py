import customtkinter as ctk
from rtl import rtl

app = ctk.CTk()

app.title("RTL Test")
app.geometry("700x400")

texts = [
    "أوردر جديد",
    "صرف الأرباح",
    "فاتورة توريد جديدة",
    "أحمد الشحات",
    "رقم الفاتورة 12345",
    "سعر البيع 150 جنيه",
    "Panadol Advance 500 mg",
    "رقم الموبايل 01012345678",
    "3 FLY 400MG 30CAP",
]

for i, text in enumerate(texts):
    ctk.CTkLabel(
        app,
        text=rtl(text),
        font=ctk.CTkFont(size=20)
    ).pack(
        pady=15,
        padx=20,
        anchor="e"
    )

app.mainloop()