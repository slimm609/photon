Summary:        Kubernetes cluster management
Name:           kubernetes
Version:        1.13.12
Release:        2%{?dist}
License:        ASL 2.0
URL:            https://github.com/kubernetes/kubernetes/archive/v%{version}.tar.gz
Source0:        kubernetes-%{version}.tar.gz
%define sha1    kubernetes-%{version}.tar.gz=a73861cff33634ba43e5c4c38dd85d8cff0ab2e0
Source1:        https://github.com/kubernetes/contrib/archive/contrib-0.7.0.tar.gz
%define sha1    contrib-0.7.0=47a744da3b396f07114e518226b6313ef4b2203c
Patch0:         k8s-1.13-vke.patch
Patch1:         go-27704.patch
Patch2:         go-27842-k8s-1.13.patch
Patch3:         CVE-2019-11250_1.13.patch
Patch4:         CVE-2020-8552-1.12-1.13.patch
Group:          Development/Tools
Vendor:         VMware, Inc.
Distribution:   Photon
BuildRequires:  go >= 1.11.2
BuildRequires:  rsync
BuildRequires:  which
Requires:       cni
Requires:       ebtables
Requires:       etcd >= 3.0.4
Requires:       ethtool
Requires:       iptables
Requires:       iproute2
Requires(pre):  /usr/sbin/useradd /usr/sbin/groupadd
Requires(postun):/usr/sbin/userdel /usr/sbin/groupdel
Requires:       socat
Requires:       (util-linux or toybox)
Requires:       cri-tools

%description
Kubernetes is an open source implementation of container cluster management.

%package        kubeadm
Summary:        kubeadm deployment tool
Group:          Development/Tools
Requires:       %{name} = %{version}
%description    kubeadm
kubeadm is a tool that enables quick and easy deployment of a kubernetes cluster.

%package	kubectl-extras
Summary:	kubectl binaries for extra platforms
Group:		Development/Tools
%description	kubectl-extras
Contains kubectl binaries for additional platforms.

%package        pause
Summary:        pause binary
Group:          Development/Tools
%description    pause
A pod setup process that holds a pod's namespace.

%global debug_package %{nil}

%prep -p exit
%setup -qn %{name}-%{version}
cd ..
tar xf %{SOURCE1} --no-same-owner
sed -i -e 's|127.0.0.1:4001|127.0.0.1:2379|g' contrib-0.7.0/init/systemd/environ/apiserver
cd %{name}-%{version}
%patch0 -p1
pushd vendor/golang.org/x/net
%patch1 -p1
%patch2 -p1
popd
%patch3 -p1
%patch4 -p1

%build
make
pushd build/pause
mkdir -p bin
gcc -Os -Wall -Werror -static -o bin/pause-amd64 pause.c
strip bin/pause-amd64
popd
make WHAT="cmd/kubectl" KUBE_BUILD_PLATFORMS="darwin/amd64 windows/amd64"

%install
install -vdm644 %{buildroot}/etc/profile.d
install -m 755 -d %{buildroot}%{_bindir}
install -m 755 -d %{buildroot}/opt/vmware/kubernetes
install -m 755 -d %{buildroot}/opt/vmware/kubernetes/darwin/amd64
install -m 755 -d %{buildroot}/opt/vmware/kubernetes/linux/amd64
install -m 755 -d %{buildroot}/opt/vmware/kubernetes/windows/amd64

binaries=(cloud-controller-manager hyperkube kube-apiserver kube-controller-manager kubelet kube-proxy kube-scheduler kubectl)
for bin in "${binaries[@]}"; do
  echo "+++ INSTALLING ${bin}"
  install -p -m 755 -t %{buildroot}%{_bindir} _output/local/bin/linux/amd64/${bin}
done
install -p -m 755 -t %{buildroot}%{_bindir} build/pause/bin/pause-amd64

# kubectl-extras
install -p -m 755 -t %{buildroot}/opt/vmware/kubernetes/darwin/amd64/ _output/local/bin/darwin/amd64/kubectl
install -p -m 755 -t %{buildroot}/opt/vmware/kubernetes/linux/amd64/ _output/local/bin/linux/amd64/kubectl
install -p -m 755 -t %{buildroot}/opt/vmware/kubernetes/windows/amd64/ _output/local/bin/windows/amd64/kubectl.exe

# kubeadm install
install -vdm644 %{buildroot}/etc/systemd/system/kubelet.service.d
install -p -m 755 -t %{buildroot}%{_bindir} _output/local/bin/linux/amd64/kubeadm
install -p -m 755 -t %{buildroot}/etc/systemd/system build/rpms/kubelet.service
install -p -m 755 -t %{buildroot}/etc/systemd/system/kubelet.service.d build/rpms/10-kubeadm.conf
sed -i '/KUBELET_CGROUP_ARGS=--cgroup-driver=systemd/d' %{buildroot}/etc/systemd/system/kubelet.service.d/10-kubeadm.conf

cd ..
# install config files
install -d -m 0755 %{buildroot}%{_sysconfdir}/%{name}
install -m 644 -t %{buildroot}%{_sysconfdir}/%{name} contrib-0.7.0/init/systemd/environ/*
cat << EOF >> %{buildroot}%{_sysconfdir}/%{name}/kubeconfig
apiVersion: v1
clusters:
- cluster:
    server: http://127.0.0.1:8080
EOF
sed -i '/KUBELET_API_SERVER/c\KUBELET_API_SERVER="--kubeconfig=/etc/kubernetes/kubeconfig"' %{buildroot}%{_sysconfdir}/%{name}/kubelet

# install service files
install -d -m 0755 %{buildroot}/usr/lib/systemd/system
install -m 0644 -t %{buildroot}/usr/lib/systemd/system contrib-0.7.0/init/systemd/*.service

# install the place the kubelet defaults to put volumes
install -dm755 %{buildroot}/var/lib/kubelet
install -dm755 %{buildroot}/var/run/kubernetes

mkdir -p %{buildroot}/%{_lib}/tmpfiles.d
cat << EOF >> %{buildroot}/%{_lib}/tmpfiles.d/kubernetes.conf
d /var/run/kubernetes 0755 kube kube -
EOF

%check
export GOPATH=%{_builddir}
go get golang.org/x/tools/cmd/cover
make %{?_smp_mflags} check

%clean
rm -rf %{buildroot}/*

%pre
if [ $1 -eq 1 ]; then
    # Initial installation.
    getent group kube >/dev/null || groupadd -r kube
    getent passwd kube >/dev/null || useradd -r -g kube -d / -s /sbin/nologin \
            -c "Kubernetes user" kube
fi

%post
chown -R kube:kube /var/lib/kubelet
chown -R kube:kube /var/run/kubernetes
systemctl daemon-reload

%post kubeadm
systemctl daemon-reload
systemctl stop kubelet
systemctl enable kubelet

%preun kubeadm
if [ $1 -eq 0 ]; then
    systemctl stop kubelet
fi

%postun
if [ $1 -eq 0 ]; then
    # Package deletion
    userdel kube
    groupdel kube
    systemctl daemon-reload
fi

%postun kubeadm
if [ $1 -eq 0 ]; then
    systemctl daemon-reload
fi

%files
%defattr(-,root,root)
%{_bindir}/cloud-controller-manager
%{_bindir}/hyperkube
%{_bindir}/kube-apiserver
%{_bindir}/kube-controller-manager
%{_bindir}/kubelet
%{_bindir}/kube-proxy
%{_bindir}/kube-scheduler
%{_bindir}/kubectl
#%{_bindir}/kubefed
%{_lib}/systemd/system/kube-apiserver.service
%{_lib}/systemd/system/kubelet.service
%{_lib}/systemd/system/kube-scheduler.service
%{_lib}/systemd/system/kube-controller-manager.service
%{_lib}/systemd/system/kube-proxy.service
%{_lib}/tmpfiles.d/kubernetes.conf
%dir %{_sysconfdir}/%{name}
%dir /var/lib/kubelet
%dir /var/run/kubernetes
%config(noreplace) %{_sysconfdir}/%{name}/config
%config(noreplace) %{_sysconfdir}/%{name}/apiserver
%config(noreplace) %{_sysconfdir}/%{name}/controller-manager
%config(noreplace) %{_sysconfdir}/%{name}/proxy
%config(noreplace) %{_sysconfdir}/%{name}/kubelet
%config(noreplace) %{_sysconfdir}/%{name}/kubeconfig
%config(noreplace) %{_sysconfdir}/%{name}/scheduler

%files kubeadm
%defattr(-,root,root)
%{_bindir}/kubeadm
/etc/systemd/system/kubelet.service
/etc/systemd/system/kubelet.service.d/10-kubeadm.conf

%files pause
%defattr(-,root,root)
%{_bindir}/pause-amd64

%files kubectl-extras
%defattr(-,root,root)
/opt/vmware/kubernetes/darwin/amd64/kubectl
/opt/vmware/kubernetes/linux/amd64/kubectl
/opt/vmware/kubernetes/windows/amd64/kubectl.exe

%changelog
*   Fri Apr 10 2020 Harinadh D <hdommaraju@vmware.com> 1.13.12-2
-   Bump up version to compile with go 1.13.5-2
*   Mon Apr 06 2020 Shreyas B <shreyasb@vmware.com> 1.13.12-1
-   Bump up version to address CVE-2019-11251.
-   Fix for CVE-2019-11250.
-   Fix for CVE-2020-8552.
*   Tue Jan 07 2020 Ashwin H <ashwinh@vmware.com> 1.13.10-2
-   Bump up version to compile with new go
*   Tue Sep 10 2019 Ashwin H <ashwinh@vmware.com> 1.13.10-1
-   Update to 1.13.10
*   Fri Aug 30 2019 Ashwin H <ashwinh@vmware.com> 1.13.6-2
-   Bump up version to compile with new go
*   Thu Aug 01 2019 Utkarsh Sahai <usahai@vmware.com> 1.13.6-1
-   Updgrade to 1.13.6 with VMware Cloud PKS patch
*   Thu May 23 2019 Ashwin H <ashwinh@vmware.com> 1.13.5-3
-   Fix CVE-2019-11244
*   Fri May 03 2019 Bo Gan <ganb@vmware.com> 1.13.5-2
-   Fix CVE-2018-17846 and CVE-2018-17143
*   Thu Apr 11 2019 Utkarsh Sahai <usahai@vmware.com> 1.13.5-1
-   Upgrade to 1.13.5 with VMware Cloud PKS patch (6f4a18cd)
