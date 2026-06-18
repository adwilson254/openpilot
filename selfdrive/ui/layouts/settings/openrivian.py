from openpilot.common.params import Params
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.list_view import button_item
from openpilot.system.ui.widgets.scroller_tici import Scroller
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets.confirm_dialog import alert_dialog

if gui_app.sunnypilot_ui():
  from openpilot.system.ui.sunnypilot.widgets.list_view import button_item_sp as button_item

class OpenRivianLayout(Widget):
  def __init__(self):
    super().__init__()
    self._params = Params()

    self._login_btn = button_item(
      lambda: tr("Rivian Account"),
      lambda: tr("LOGIN"),
      lambda: tr("Authenticate with your Rivian account to enable ABRP routes and API features."),
      callback=self._on_rivian_login
    )

    self._scroller = Scroller([self._login_btn], line_separator=True, spacing=0)

  def _render(self, rect):
    self._scroller.render(rect)

  def show_event(self):
    super().show_event()
    self._scroller.show_event()

  def _on_rivian_login(self):
    from openpilot.system.ui.widgets.keyboard import Keyboard
    from openpilot.selfdrive.openrivian.api.rivian_api import RivianAPI
    
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
                        gui_app.push_widget(alert_dialog("Rivian Authentication Successful!"))
                    except Exception as e:
                      gui_app.push_widget(alert_dialog(f"MFA Failed: {e}"))
                otp_kb.set_callback(otp_cb)
                gui_app.push_widget(otp_kb)
              else:
                gui_app.push_widget(alert_dialog("Rivian Authentication Successful!"))
            except Exception as e:
              gui_app.push_widget(alert_dialog(f"Login Failed: {e}"))
        password_kb.set_callback(pass_cb)
        gui_app.push_widget(password_kb)
    email_kb.set_callback(email_cb)
    gui_app.push_widget(email_kb)
