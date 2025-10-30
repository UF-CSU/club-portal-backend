// email_templates/src/invite.tsx
import {
  Body,
  Button,
  Column,
  Container,
  Head,
  Hr,
  Html,
  Img,
  Link,
  Preview,
  Row,
  Section,
  Text,
} from "@react-email/components";
import * as React from "react";

type Props = {
  setup_url: string;
};
const styles: Record<string, React.CSSProperties> = {
  main: {
    backgroundColor: "#f6f9fc",
    margin: 0,
    padding: "24px 0",
  },
};

export default function InviteEmail({ setup_url = "{{ setup_url }}" }: Props) {
  return (
    <Html>
      <Head />
      <Body style={main}>
        <Preview>Set up your account with CSU!</Preview>
        <Container style={container}>
          <Section style={logo}>
            <Img
              width={114}
              src={`https://ufcsu.org/csu_logo.svg`}
              alt="CSU"
              style={logoImg}
            />
          </Section>
          <Section style={sectionsBorders}>
            <Row>
              <Column style={sectionBorder} />
              <Column style={sectionCenter} />
              <Column style={sectionBorder} />
            </Row>
          </Section>
          <Section style={content}>
            <Text style={paragraph}>Welcome To CSU!</Text>
            <Text style={paragraph}>
              Please set up your account at the following link:{" "}
              <Link href={`${setup_url}`}>Click Here!</Link>
              <br />
              <br />
              If that doesn't work for you, copy and paste the link below into
              your browser:
              <br />
              <Link>{setup_url}</Link>
              <br />
              <br />
              Thanks,
              <br />
              CSU Team
            </Text>
          </Section>
        </Container>

        <Section style={footer}>
          <Row>
            <Text style={{ textAlign: "center", color: "#706a7b" }}>
              © 2025 CSU
              <br />
              University of Florida, Gainesville, FL
            </Text>
          </Row>
        </Section>
      </Body>
    </Html>
  );
}

const fontFamily = "HelveticaNeue,Helvetica,Arial,sans-serif";

const main = {
  backgroundColor: "#efeef1",
  fontFamily,
};

const paragraph = {
  lineHeight: 1.5,
  fontSize: 14,
};

const container = {
  maxWidth: "580px",
  margin: "30px auto",
  backgroundColor: "#ffffff",
};

const footer = {
  maxWidth: "580px",
  margin: "0 auto",
};

const content = {
  padding: "5px 20px 10px 20px",
};

const logo = {
  padding: 30,
};

const logoImg = {
  margin: "0 auto",
};

const sectionsBorders = {
  width: "100%",
};

const sectionBorder = {
  borderBottom: "1px solid rgb(238,238,238)",
  width: "249px",
};

const sectionCenter = {
  borderBottom: "1px solid #0f44cd",
  width: "102px",
};

const link = {
  textDecoration: "underline",
};
