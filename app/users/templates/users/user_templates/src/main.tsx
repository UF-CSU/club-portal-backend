import React from "react";
import { createRoot } from "react-dom/client";
import InviteEmail from "./account-setup-link";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <InviteEmail setup_url="{{ setup_url }}" />
  </React.StrictMode>
);
