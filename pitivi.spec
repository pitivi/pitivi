%define glib2_version 2.4.0
%define gtk2_version 2.4.0
%define pango_version 1.5.0

Summary: Pitivi non linear video editor under linux 
Name: pitivi
Version: @VERSION@
Release: 1
Source0: %{name}-%{version}.tar.gz
Packager: casano_g@epita.fr
License: GPL (cf http://www.pitivi.org)
Group: NLE
URL: http://www.pitivi.org
Vendor: Edward Hervey Guillaume Casanova Stephan Bloch Raphael Pralat Marc Deletrez 

BuildRequires:  glib2-devel >= %{glib2_version}
BuildRequires:  gtk2-devel >= %{gtk2_version}
BuildRequires:  pango-devel >= %{pango_version}
BuildRequires:  gstreamer-devel => @GST_MAJORMINOR@

Requires:	gstreamer >= @GST_MAJORMINOR@

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

%description
Pitivi is a Non Linear Video Editor using the popular GStreamer media framework

%prep
%setup -q

%build
%configure
make

%install
rm -rf $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc AUTHORS COPYING ChangeLog NEWS README
%{_datadir}/pixmaps/pitivi
%{_datadir}/pitivi/ui/*.xml
%{_datadir}/locale/*
%{_libdir}/*
%{_bindir}/pitivi

%changelog
* Thu Dec  2 2004 root <root@pas-r06p01.pas.epita.fr> - 
- Initial build.
