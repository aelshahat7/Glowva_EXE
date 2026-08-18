warning: in the working copy of 'main.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/main.py b/main.py[m
[1mindex bddf155..107e975 100644[m
[1m--- a/main.py[m
[1m+++ b/main.py[m
[36m@@ -492,6 +492,11 @@[m [mclass GlowvaApp(ctk.CTk):[m
             warn_frame.pack_slaves()[-1].pack(pady=(2, 12))[m
 [m
 [m
[32m+[m[32mprint("TEST 1:", rtl("أوردر جديد"))[m
[32m+[m[32mprint("TEST 2:", rtl("صرف الأرباح"))[m
[32m+[m[32mprint("TEST 3:", rtl("فاتورة توريد جديدة"))[m
[32m+[m[32mprint("TEST 4:", rtl("أحمد الشحات"))[m
[32m+[m[32mprint("TEST 5:", rtl("رقم الفاتورة 12345"))[m
 if __name__ == "__main__":[m
     app = GlowvaApp()[m
     app.mainloop()[m
\ No newline at end of file[m
