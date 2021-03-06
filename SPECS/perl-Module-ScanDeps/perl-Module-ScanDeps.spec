# Got the intial spec from Fedora and modified it
Summary:        Recursively scan Perl code for dependencies
Name:           perl-Module-ScanDeps
Version:        1.28
Release:        1%{?dist}
License:        GPL+ or Artistic
Group:          Development/Libraries
Source0:        https://cpan.metacpan.org/authors/id/R/RS/RSCHUPP/Module-ScanDeps-%{version}.tar.gz
%define sha1 Module-ScanDeps=d44fa0e4dde3db9424349e9a8844ad0fba2daa28
URL:            http://search.cpan.org/dist/Module-ScanDeps/
Vendor:         VMware, Inc.
Distribution:   Photon
BuildArch:      noarch
BuildRequires:  perl
Requires:       perl

%description
This module scans potential modules used by perl programs and returns a
hash reference.  Its keys are the module names as they appear in %%INC (e.g.
Test/More.pm).  The values are hash references.

%prep
%setup -q -n Module-ScanDeps-%{version}

%build
perl Makefile.PL INSTALLDIRS=vendor NO_PACKLIST=1
make %{?_smp_mflags}

%install
make pure_install DESTDIR=%{buildroot}
find %{buildroot} -type f -name .packlist -exec rm -f {} +
%{_fixperms} %{buildroot}

%check
export PERL_MM_USE_DEFAULT=1
cpan local::lib
cpan Test::Requires
make %{?_smp_mflags} test

%files
%{_bindir}/scandeps.pl
%{perl_vendorlib}/Module/
%{_mandir}/man1/scandeps.pl.1*
%{_mandir}/man3/*

%changelog
*   Thu Aug 20 2020 Gerrit Photon <photon-checkins@vmware.com> 1.28-1
-   Automatic Version Bump
*   Fri Sep 21 2018 Dweep Advani <dadvani@vmware.com> 1.25-1
-   Update to version 1.25
*   Wed Apr 05 2017 Robert Qi <qij@vmware.com> 1.23-1
-   Update version to 1.23
*   Wed Oct 05 2016 ChangLee <changlee@vmware.com> 1.18-3
-   Modified %check
*   Tue May 24 2016 Priyesh Padmavilasom <ppadmavilasom@vmware.com> 1.18-2
-   GA - Bump release of all rpms
*   Fri Apr 3 2015 Divya Thaluru <dthaluru@vmware.com> 1.18-1
-   Initial version.
