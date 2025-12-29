import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import "./index.css";

initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        lazy: () => import("./pages/labs")
    },
    {
        path: "/labs",
        lazy: () => import("./pages/labs")
    },
    {
        path: "*",
        lazy: () => import("./pages/NoPage")
    }
]);

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);

root.render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
