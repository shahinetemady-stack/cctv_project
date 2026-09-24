from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("",                        views.LeadListView.as_view(),    name="lead-list"),
    path("import/",                 views.LeadImportView.as_view(),  name="lead-import"),
    path("export/",                 views.LeadExportView.as_view(),  name="lead-export"),
    path("meta/",                   views.LeadMetaView.as_view(),    name="lead-meta"),
    path("settings/",               views.LeadSettingsView.as_view(), name="lead-settings"),
    path("run/<str:source>/",       views.ScraperRunView.as_view(),  name="lead-run"),
    path("campaigns/",              views.CampaignListView.as_view(),   name="campaign-list"),
    path("campaigns/<int:pk>/send/", views.CampaignSendView.as_view(),  name="campaign-send"),
    path("<int:pk>/",               views.LeadDetailView.as_view(),  name="lead-detail"),
]
