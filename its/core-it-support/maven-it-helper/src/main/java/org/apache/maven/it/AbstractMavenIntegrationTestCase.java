/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.maven.it;

import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.TestInfo;

/**
 * @author Jason van Zyl
 * @author Kenney Westerhof
 */
public abstract class AbstractMavenIntegrationTestCase {
    /**
     * Save System.out for progress reports etc.
     */
    private static PrintStream out = System.out;

    private static final String SHARED_FIXTURE = "mng-0095";

    private final Map<String, Path> isolatedFixtures = new HashMap<>();

    private String testName;

    protected AbstractMavenIntegrationTestCase() {}

    @BeforeAll
    static void setupInputStream() {
        if (!(System.in instanceof NonCloseableInputStream)) {
            System.setIn(new NonCloseableInputStream(System.in));
        }
    }

    @BeforeEach
    void setupContext(TestInfo testInfo) {
        testName = testInfo.getTestMethod().get().getName();
    }

    protected String getName() {
        return testName;
    }



    private static class NonCloseableInputStream extends FilterInputStream {
        NonCloseableInputStream(InputStream delegate) {
            super(delegate);
        }

        @Override
        public void close() throws IOException {}
    }



    /**
     * Extracts test resources to a temporary directory.
     *
     * @param resourcePath The path to the resource directory, must not be <code>null</code>.
     * @return The path to the extracted resources, never <code>null</code>.
     * @throws IOException If the resources could not be extracted.
     * @since 4.0.0
     */
    protected Path extractResources(String resourcePath) throws IOException {
        // Strip leading '/' to keep resolve() relative (unlike new File(parent, "/child")
        // which silently strips it, Path.resolve("/child") replaces the base entirely)
        if (resourcePath.startsWith("/")) {
            resourcePath = resourcePath.substring(1);
        }
        Path sharedRoot = Paths.get(
                System.getProperty("maven.test.tmpdir", System.getProperty("java.io.tmpdir")));
        if (SHARED_FIXTURE.equals(resourcePath)) {
            return isolateSharedFixture(sharedRoot, resourcePath);
        }
        return sharedRoot.resolve(resourcePath).toAbsolutePath();
    }

    private Path isolateSharedFixture(Path sharedRoot, String resourcePath) throws IOException {
        Path cached = isolatedFixtures.get(resourcePath);
        if (cached != null) {
            return cached;
        }
        Path source = sharedRoot.resolve(resourcePath).toAbsolutePath();
        if (!Files.isDirectory(source)) {
            throw new IOException("shared fixture is missing: " + source);
        }
        String method = testName == null ? "setup" : testName;
        String key = getClass().getName() + "." + method;
        Path dest = sharedRoot
                .resolveSibling("it-fixtures")
                .resolve(key)
                .resolve(resourcePath)
                .toAbsolutePath();
        if (Files.exists(dest)) {
            throw new IOException("shared fixture collision for " + key + ": " + dest);
        }
        copyFixtureTree(source, dest);
        isolatedFixtures.put(resourcePath, dest);
        return dest;
    }

    private static void copyFixtureTree(Path source, Path dest) throws IOException {
        try (Stream<Path> walk = Files.walk(source)) {
            for (Path from : walk.toList()) {
                Path to = dest.resolve(source.relativize(from));
                if (Files.isDirectory(from)) {
                    Files.createDirectories(to);
                } else {
                    Files.createDirectories(to.getParent());
                    Files.copy(from, to, StandardCopyOption.REPLACE_EXISTING);
                }
            }
        }
    }

    private static void deleteTree(Path root) throws IOException {
        try (Stream<Path> walk = Files.walk(root)) {
            for (Path path : walk.sorted(Comparator.reverseOrder()).toList()) {
                Files.deleteIfExists(path);
            }
        }
    }

    @Deprecated
    protected Verifier newVerifier(String basedir) throws VerificationException {
        return newVerifier(basedir, true);
    }

    protected Verifier newVerifier(Path basedir) throws VerificationException {
        return newVerifier(basedir, true);
    }

    @Deprecated
    protected Verifier newVerifier(String basedir, String settings) throws VerificationException {
        return newVerifier(basedir, settings, true);
    }

    protected Verifier newVerifier(Path basedir, String settings) throws VerificationException {
        return newVerifier(basedir, settings, true);
    }

    @Deprecated
    protected Verifier newVerifier(String basedir, boolean createDotMvn) throws VerificationException {
        return newVerifier(basedir, "remote", createDotMvn);
    }

    protected Verifier newVerifier(Path basedir, boolean createDotMvn) throws VerificationException {
        return newVerifier(basedir, "remote", createDotMvn);
    }

    @Deprecated
    protected Verifier newVerifier(String basedir, String settings, boolean createDotMvn) throws VerificationException {
        return newVerifier(Paths.get(basedir), settings, createDotMvn);
    }

    protected Verifier newVerifier(Path basedir, String settings, boolean createDotMvn) throws VerificationException {
        Verifier verifier = new Verifier(basedir, null, createDotMvn);

        // try to get jacoco arg from command line if any then use it to start IT to populate jacoco data
        // we use a different file than the main one
        ProcessHandle.current()
                .info()
                .arguments()
                .flatMap(strings -> Arrays.stream(strings)
                        .filter(s -> s.contains("-javaagent:") && s.contains("org.jacoco.agent"))
                        .findFirst())
                .map(s -> s.replace("jacoco.exec", "jacoco-its.exec"))
                .ifPresent(verifier::addJvmArgument);

        verifier.setAutoclean(false);

        if (settings != null) {
            Path settingsPath;
            if (!settings.isEmpty()) {
                settingsPath = Paths.get("settings-" + settings + ".xml");
            } else {
                settingsPath = Paths.get("settings.xml");
            }

            if (!settingsPath.isAbsolute()) {
                String settingsDir = System.getProperty("maven.it.global-settings.dir", "");
                if (!settingsDir.isEmpty()) {
                    settingsPath = Paths.get(settingsDir).resolve(settingsPath);
                } else {
                    //
                    // Make is easier to run ITs from m2e in Maven IT mode without having to set any additional
                    // properties.
                    //
                    settingsPath = Paths.get("target/test-classes").resolve(settingsPath);
                }
            }

            String path = settingsPath.toAbsolutePath().toString();
            verifier.addCliArgument("--install-settings");
            if (path.indexOf(' ') < 0) {
                verifier.addCliArgument(path);
            } else {
                verifier.addCliArgument('"' + path + '"');
            }
        }

        // auto set source+target to lowest reasonable java version
        verifier.getSystemProperties().put("maven.compiler.source", "8");
        verifier.getSystemProperties().put("maven.compiler.target", "8");
        verifier.getSystemProperties().put("maven.compiler.release", "8");

        return verifier;
    }

    public static void fail(String message) {
        org.junit.jupiter.api.Assertions.fail(message);
    }
}
