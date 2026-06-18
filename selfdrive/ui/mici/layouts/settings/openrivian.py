from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigInputDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.openrivian.api.rivian_api import RivianAPI

class OpenRivianLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._login_btn = BigButton("Rivian Account", "LOGIN", scroll=False)
    self._login_btn.set_click_callback(self._on_rivian_login)
    
    self._scroller.add_widgets([self._login_btn])
    
  def _on_rivian_login(self):
    def email_cb(email: str):
      if email:
        def pass_cb(password: str):
          if password:
            try:
              api = RivianAPI()
              auth_res = api.login(email, password)
              if auth_res["status"] == "mfa_required":
                def otp_cb(otp: str):
                  if otp:
                    try:
                      mfa_res = api.login_with_otp(otp)
                      if mfa_res["status"] == "success":
                        gui_app.push_widget(BigDialog("Success", "Rivian Authentication Successful!"))
                    except Exception as e:
                      gui_app.push_widget(BigDialog("Error", f"MFA Failed: {e}"))
                gui_app.push_widget(BigInputDialog("Enter the 6-digit SMS code", "", confirm_callback=otp_cb))
              else:
                gui_app.push_widget(BigDialog("Success", "Rivian Authentication Successful!"))
            except Exception as e:
              gui_app.push_widget(BigDialog("Error", f"Login Failed: {e}"))
        gui_app.push_widget(BigInputDialog("Enter your Rivian password", "", confirm_callback=pass_cb, password_mode=True))
    gui_app.push_widget(BigInputDialog("Enter your Rivian account email", "", confirm_callback=email_cb))
