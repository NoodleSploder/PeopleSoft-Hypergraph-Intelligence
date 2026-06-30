(function () {
    const LINKS = [
        { label: "Home", href: "/static/index.html" },
        { label: "API Docs", href: "/docs" },
        { label: "Tracing Config", href: "/api/tracing/config" },
        { label: "Live Events", href: "/api/live/events" },
        { label: "IB Nodes", href: "/api/ib/nodes" },
        { label: "Build HCM Graph", href: "/api/graph/build?env=HCM" },
        { label: "Build FSCM Graph", href: "/api/graph/build?env=FSCM" },
    ];

    function isActive(href) {
        const currentPath = window.location.pathname;
        const currentSearch = window.location.search;
        const url = new URL(href, window.location.origin);

        if (url.pathname === "/static/index.html" && (currentPath === "/" || currentPath === "/static/index.html")) {
            return true;
        }

        if (url.pathname !== currentPath) {
            return false;
        }

        if (!url.search) {
            return true;
        }

        return url.search === currentSearch;
    }

    function createBanner() {
        if (document.querySelector(".pe-shell-banner")) {
            return;
        }

        const banner = document.createElement("div");
        banner.className = "pe-shell-banner";

        const brand = document.createElement("a");
        brand.className = "pe-shell-brand";
        brand.href = "/static/index.html";
        brand.textContent = "PeopleSoft Explorer";
        banner.appendChild(brand);

        const nav = document.createElement("nav");
        nav.className = "pe-shell-nav";
        nav.setAttribute("aria-label", "PeopleSoft Explorer navigation");

        LINKS.forEach((item) => {
            const link = document.createElement("a");
            link.href = item.href;
            link.textContent = item.label;
            if (isActive(item.href)) {
                link.className = "active";
                link.setAttribute("aria-current", "page");
            }
            nav.appendChild(link);
        });

        banner.appendChild(nav);
        document.body.insertBefore(banner, document.body.firstChild);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createBanner);
    } else {
        createBanner();
    }
}());
