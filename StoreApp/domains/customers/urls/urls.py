from django.urls import path

from StoreApp.domains.customers.views import (
    CustomerAddressDetailView,
    CustomerAddressListCreateView,
    CustomerGoogleAuthView,
    CustomerGoogleConfigView,
    CustomerLoginView,
    CustomerLogoutView,
    CustomerMembershipListView,
    CustomerMeView,
    CustomerPasswordResetConfirmView,
    CustomerPasswordResetRequestView,
    CustomerProfileView,
    CustomerRefreshView,
    CustomerRegisterView,
    CustomerVerifyEmailResendView,
    CustomerVerifyEmailView,
)

#=========================================
# CUSTOMERS — auth de compradores (/api/customer-auth/*) + perfil
# (/api/customer/*). La cuenta del comprador es SEPARADA de la cuenta
# DAVENT del dueño (auth.User): JWT propio con cookies customer_*.
#=========================================
urlpatterns = [
    #AUTH DE COMPRADORES
    path('customer-auth/register/',                  CustomerRegisterView.as_view(),                 name = 'customer_register'),
    path('customer-auth/login/',                     CustomerLoginView.as_view(),                    name = 'customer_login'),
    path('customer-auth/refresh/',                   CustomerRefreshView.as_view(),                  name = 'customer_refresh'),
    path('customer-auth/logout/',                    CustomerLogoutView.as_view(),                   name = 'customer_logout'),
    path('customer-auth/me/',                        CustomerMeView.as_view(),                       name = 'customer_me'),
    path('customer-auth/verify-email/',              CustomerVerifyEmailView.as_view(),              name = 'customer_verify_email'),
    path('customer-auth/verify-email/resend/',       CustomerVerifyEmailResendView.as_view(),        name = 'customer_verify_email_resend'),
    path('customer-auth/password-reset/',            CustomerPasswordResetRequestView.as_view(),     name = 'customer_password_reset'),
    path('customer-auth/password-reset/confirm/',    CustomerPasswordResetConfirmView.as_view(),     name = 'customer_password_reset_confirm'),
    #GOOGLE LOGIN (por tienda — client propio BYO o central DAVENT)
    path('customer-auth/google-config/<slug:store_slug>/', CustomerGoogleConfigView.as_view(),      name = 'customer_google_config'),
    path('customer-auth/google/',                    CustomerGoogleAuthView.as_view(),               name = 'customer_google'),
    #PERFIL + DIRECCIONES + MEMBRESÍAS (Bearer customer_access)
    path('customer/profile/',                        CustomerProfileView.as_view(),                  name = 'customer_profile'),
    path('customer/addresses/',                      CustomerAddressListCreateView.as_view(),        name = 'customer_addresses'),
    path('customer/addresses/<int:pk>/',             CustomerAddressDetailView.as_view(),            name = 'customer_address_detail'),
    path('customer/memberships/',                    CustomerMembershipListView.as_view(),           name = 'customer_memberships'),
]
