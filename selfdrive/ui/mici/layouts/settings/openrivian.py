from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigParamControl
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigInputDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.openrivian.api.rivian_api import RivianAPI

# Per-service toggles. The OpenRivian daemons default to ON; enabling a toggle DISABLES
# that one service (leaving the others running) so you can isolate which service is
# causing an issue. Maps to the OpenRivian<Svc>Disabled params read by process_gating.
_SERVICE_TOGGLES = [
    ("disable rivian api", "OpenRivianApiDisabled"),
    ("disable mqtt broker", "OpenRivianBrokerDisabled"),
    ("disable telemetry (cereal to mqtt)", "OpenRivianTelemetryDisabled"),
    ("disable settings publish", "OpenRivianSettingsPublishDisabled"),
    ("disable web dashboard", "OpenRivianWebDashboardDisabled"),
]


class OpenRivianLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._login_btn = BigButton("Rivian Account", "LOGIN", scroll=False)
    self._login_btn.set_click_callback(self._on_rivian_login)

    # ON = that service is disabled. Restart takes effect on the next manager cycle.
    self._service_toggles = [BigParamControl(label, param) for label, param in _SERVICE_TOGGLES]

    self._scroller.add_widgets([self._login_btn, *self._service_toggles])
    
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
