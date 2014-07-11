/*
 * (C) Copyright 2014 Nuxeo SA (http://nuxeo.com/) and contributors.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the GNU Lesser General Public License
 * (LGPL) version 2.1 which accompanies this distribution, and is available at
 * http://www.gnu.org/licenses/lgpl-2.1.html
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * Contributors:
 *     Antoine Taillefer <ataillefer@nuxeo.com>
 */
package org.nuxeo.drive.adapter.impl;

import static org.nuxeo.ecm.platform.query.nxql.CoreQueryDocumentPageProvider.CORE_SESSION_PROPERTY;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.nuxeo.drive.adapter.FileSystemItem;
import org.nuxeo.drive.adapter.FolderItem;
import org.nuxeo.drive.service.NuxeoDriveManager;
import org.nuxeo.ecm.core.api.ClientException;
import org.nuxeo.ecm.core.api.CoreSession;
import org.nuxeo.ecm.core.api.DocumentModel;
import org.nuxeo.ecm.core.api.security.SecurityConstants;
import org.nuxeo.ecm.platform.query.api.PageProvider;
import org.nuxeo.ecm.platform.query.api.PageProviderService;
import org.nuxeo.runtime.api.Framework;

/**
 * Default implementation of a collection {@link FolderItem}.
 *
 * @author Antoine Taillefer
 */
public class CollectionSyncRootFolderItem extends DefaultSyncRootFolderItem
        implements FolderItem {

    private static final long serialVersionUID = 1L;

    public CollectionSyncRootFolderItem(String factoryName,
            FolderItem parentItem, DocumentModel doc) throws ClientException {
        super(factoryName, parentItem, doc);
        // A sync root can be renamed if the current user has the
        // WriteProperties permission on it
        // TODO
        this.canRename = doc.getCoreSession().hasPermission(doc.getRef(),
                SecurityConstants.WRITE_PROPERTIES);
        // A sync root can be deleted since deletion is implemented as
        // unregistration
        this.canDelete = true;
    }

    protected CollectionSyncRootFolderItem() {
        // Needed for JSON deserialization
    }

    @Override
    public void delete() throws ClientException {
        CoreSession session = getSession();
        DocumentModel doc = getDocument(session);
        Framework.getLocalService(NuxeoDriveManager.class).unregisterSynchronizationRoot(
                principal, doc, session);
    }

    @Override
    public boolean canMove(FolderItem dest) throws ClientException {
        return false;
    }

    @Override
    public FileSystemItem move(FolderItem dest) throws ClientException {
        throw new UnsupportedOperationException(
                "Cannot move a synchronization root folder item.");
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<FileSystemItem> getChildren() throws ClientException {

        PageProviderService pageProviderService = Framework.getLocalService(PageProviderService.class);
        Map<String, Serializable> props = new HashMap<String, Serializable>();
        props.put(CORE_SESSION_PROPERTY, (Serializable) getSession());
        PageProvider<DocumentModel> childrenPageProvider = (PageProvider<DocumentModel>) pageProviderService.getPageProvider(
                "default_content_collection", null, null, 0L, props, docId);
        List<DocumentModel> dmChildren = childrenPageProvider.getCurrentPage();

        List<FileSystemItem> children = new ArrayList<FileSystemItem>(
                dmChildren.size());
        for (DocumentModel dmChild : dmChildren) {
            FileSystemItem child = getFileSystemItemAdapterService().getFileSystemItem(
                    dmChild, this);
            if (child != null) {
                children.add(child);
            }
        }
        return children;
    }

}
