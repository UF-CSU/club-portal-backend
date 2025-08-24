// email_templates/src/invite.tsx
import {
  Body,
  Button,
  Container,
  Head,
  Hr,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from "@react-email/components";
import * as React from "react";

type Props = {
  club_name: string;        
  invite_url?: string;       
  logo_url?: string;      
}
const styles: Record<string, React.CSSProperties> = {
  main: {
    backgroundColor: "#f6f9fc",
    margin: 0,
    padding: "24px 0",
  },
  container: {
    backgroundColor: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "28px",
    width: "100%",
    maxWidth: "600px",
  },
  heading: {
    fontSize: "20px",
    fontWeight: 600,
    margin: "0 0 12px 0",
    color: "#111827",
    fontFamily: "'Sora', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  text: {
    fontSize: "14px",
    lineHeight: "22px",
    color: "#374151",
    margin: "0 0 16px 0",
    fontFamily: "'Sora', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  button: {
    backgroundColor: "#0f44cd",
    color: "#ffffff",
    borderRadius: "6px",
    display: "inline-block",
    padding: "12px 18px",
    textDecoration: "none",
    fontSize: "14px",
    fontWeight: 600,
    fontFamily: "'Sora', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    marginBottom: "24px", 
  },
  link: {
    color: "#111827",
    textDecoration: "underline",
    fontFamily: "'Sora', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  hr: {
    borderColor: "#e5e7eb",
    margin: "20px 0",
  },
  footer: {
    fontSize: "12px",
    color: "#6b7280",
    fontFamily: "'Sora', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
};



export default function InviteEmail({
  club_name = "{{ club_name }}",
  invite_url = "{{ invite_url }}",
  logo_url = "{{ logo_url }}",
}: Props) {
  return (
    <Html>
      <Head>
        <link
          href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </Head>
      <Preview>You’re invited to join {club_name}</Preview>
      <Body style={styles.main}>
        <Container style={styles.container}>
          <img
            src={logo_url}
            width="40"
            height="33"
            alt={{club_name} + "Logo"}
          />
          <Section>
            <h1 style={styles.heading}>You’ve been added to {club_name}</h1>
            <Text style={styles.text}>
              Click the button below to accept your invite and finish setting up
              access.
            </Text>

            <Button style={styles.button} href={invite_url}>
              Accept invite
            </Button>

            <Text style={styles.text}>
              If the button doesn’t work, copy and paste this URL into your
              browser:
              <br />
              <Link style={styles.link} href={invite_url}>
                {invite_url}
              </Link>
            </Text>

            <Hr style={styles.hr} />
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

// (Optional) Preview props for local dev with react-email
// InviteEmail.PreviewProps = {
//   club_name: "UF Computing Student Union",
//   invite_url: "https://example.com/invite/ABC123",
//   support_url: "https://example.com/support",
// } as Props;
