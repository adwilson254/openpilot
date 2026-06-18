from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets import DialogResult
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.openrivian.api.rivian_api import RivianAPI

class OpenRivianLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._login_btn = BigButton("Rivian Account", "LOGIN", scroll=False)
    self._login_btn.set_click_callback(self._on_rivian_login)
    
    self._scroller.add_widgets([self._login_btn])
    
  def _on_rivian_login(self):
    email_kb = Keyboard(show_password_toggle=False)
    email_kb.set_title("Rivian Login", "Enter your Rivian account email")
    
    def email_cb(res1):
      if res1 == DialogResult.CONFIRM:
        email = email_kb.text
        password_kb = Keyboard(show_password_toggle=True, password_mode=True)
        password_kb.set_title("Rivian Login", "Enter your Rivian password")
        
        def pass_cb(res2):
          if res2 == DialogResult.CONFIRM:
            password = password_kb.text
            try:
              api = RivianAPI()
              auth_res = api.login(email, password)
              if auth_res["status"] == "mfa_required":
                otp_kb = Keyboard(max_text_size=6)
                otp_kb.set_title("Rivian 2FA", "Enter the 6-digit SMS code")
                def otp_cb(res3):
                  if res3 == DialogResult.CONFIRM:
                    try:
                      mfa_res = api.login_with_otp(otp_kb.text)
                      if mfa_res["status"] == "success":
                        gui_app.push_widget(BigDialog("Success", "Rivian Authentication Successful!"))
                    except Exception as e:
                      gui_app.push_widget(BigDialog("Error", f"MFA Failed: {e}"))
                otp_kb.set_callback(otp_cb)
                gui_app.push_widget(otp_kb)
              else:
                gui_app.push_widget(BigDialog("Success", "Rivian Authentication Successful!"))
            except Exception as e:
              gui_app.push_widget(BigDialog("Error", f"Login Failed: {e}"))
        password_kb.set_callback(pass_cb)
        gui_app.push_widget(password_kb)
    email_kb.set_callback(email_cb)
    gui_app.push_widget(email_kb)
